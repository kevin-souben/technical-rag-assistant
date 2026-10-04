"""Tests de src/notebooks.py : sans Ollama ni modèle d'embeddings, dans un dossier temporaire.

Usage :
    python -m tests.test_notebooks
"""
import tempfile
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import DeterministicFakeEmbedding

from src import config, notebooks, vector_store

# faux embeddings (vecteurs déterministes) : la base Chroma est réelle, le modèle n'est pas chargé
vector_store.get_embeddings = lambda: DeterministicFakeEmbedding(size=32)


def raises(exception, func, *args) -> bool:
    try:
        func(*args)
    except exception:
        return True
    return False


def test_slugs() -> None:
    for slug in ["abc", "carte-mere", "a1-b2", "x" * 40]:
        assert notebooks.validate_slug(slug) == slug
    for slug in ["", ".", "..", "a/b", "a\\b", "../x", "Abc", "a b", "-a", "a-", "a--b",
                 "x" * 41, "esp32", "msi", "_legacy_chats", None]:
        assert raises(ValueError, notebooks.validate_slug, slug), slug
    assert notebooks.slugify("Carte mère MSI !") == "carte-mere-msi"


def test_refusals(root: Path) -> None:
    data = config.BASE_DIR / "data"
    # hors du dossier des notebooks, ou dans une base protégée
    for target in [root, root / "..", root.parent / "autre", data / "chroma_db",
                   data / "raw_pdfs", data / "extracted_images", root / "a" / ".." / ".."]:
        assert raises(PermissionError, notebooks._check_inside, target), target
    # notebooks hérités : ni suppression, ni ajout, ni retrait de PDF
    assert raises(PermissionError, notebooks.delete_notebook, "esp32")
    assert raises(PermissionError, notebooks.add_pdf, "esp32", b"%PDF-1.4", "a.pdf", False)
    assert raises(PermissionError, notebooks.remove_source, "esp32", "esp32_datasheet_en.pdf")
    # identifiants dangereux
    for slug in ["../chroma_db", "..", ".", "a/b", "inconnu"]:
        assert raises(ValueError, notebooks.delete_notebook, slug), slug


def test_fake_pdf(slug: str) -> None:
    for data, name in [(b"hello", "a.pdf"),           # ne commence pas par %PDF
                       (b"%PDF-1.4", "a.txt"),        # mauvaise extension
                       (b"%PDF-1.4", "../"),          # pas de nom de fichier
                       (b"%PDF-1.4", ".pdf"),         # nom vide
                       (b"%PDF-1.4", "a|b.pdf"),      # caractère interdit
                       ("%PDF-1.4", "a.pdf")]:        # texte, pas des octets
        assert raises(ValueError, notebooks.add_pdf, slug, data, name, False), name
    max_bytes = notebooks.MAX_PDF_BYTES
    notebooks.MAX_PDF_BYTES = 10                      # évite de créer 200 Mo en mémoire
    assert raises(ValueError, notebooks.add_pdf, slug, b"%PDF-1.4 trop long", "a.pdf", False)
    notebooks.MAX_PDF_BYTES = max_bytes
    # commence par %PDF mais illisible : refusé avant toute écriture
    assert raises(ValueError, notebooks.add_pdf, slug, b"%PDF-1.4 faux", "faux.pdf", False)
    assert notebooks._clean_pdf_name("C:\\Users\\x\\..\\doc.PDF") == "doc.PDF"
    assert not list((Path(config.NOTEBOOKS_DIR) / slug / "pdfs").iterdir())  # rien d'écrit


def test_chat(slug: str) -> None:
    entry = {"id": "1", "timestamp": "2026-10-04T10:00:00", "question": "Q ?", "answer": "R [1]",
             "refused": False, "truncated": False, "warnings": [],
             "cited": [{"number": 1, "label": "a.pdf | page 1 | text", "image_path": None}],
             "timings": {"retrieval": 0.1, "first_token": 1.0, "total": 2.0}}
    assert notebooks.load_chat(slug) == []
    notebooks.append_chat(slug, entry)
    notebooks.append_chat(slug, {**entry, "id": "2"})
    assert [e["id"] for e in notebooks.load_chat(slug)] == ["1", "2"]
    assert notebooks.load_chat(slug)[0] == entry
    # jamais d'objet Document, jamais d'entrée incomplète
    assert raises(ValueError, notebooks.append_chat, slug, {**entry, "cited": [Document("x")]})
    assert raises(ValueError, notebooks.append_chat, slug, {"id": "3"})
    notebooks.clear_chat(slug)
    assert notebooks.load_chat(slug) == []
    # historique d'un notebook hérité : rangé dans _legacy_chats, pas dans data/chroma_db
    notebooks.append_chat("esp32", entry)
    assert (Path(config.NOTEBOOKS_DIR) / "_legacy_chats" / "esp32.json").exists()
    assert notebooks.load_chat("esp32") == [entry]


def test_create_and_delete() -> str:
    slug = notebooks.create_notebook("Test suppression")
    assert slug == "test-suppression"
    assert raises(ValueError, notebooks.create_notebook, "Test suppression")  # déjà existant
    assert slug in [nb["slug"] for nb in notebooks.list_notebooks()]

    # vraie base Chroma : on écrit, on relit, on cherche (fichiers ouverts par Chroma)
    store = notebooks.open_store(slug)
    store.add_texts(["CR2032 battery", "ATX power"], ids=["a::1", "a::2"],
                    metadatas=[{"source": "a.pdf", "page": 1, "chunk_id": "a::1"},
                               {"source": "a.pdf", "page": 2, "chunk_id": "a::2"}])
    assert notebooks.list_sources(slug) == [{"source": "a.pdf", "entries": 2}]
    assert len(store.similarity_search("battery", k=1)) == 1
    assert notebooks.remove_source(slug, "a.pdf") == 2
    assert notebooks.list_sources(slug) == []
    store.add_texts(["again"], ids=["b::1"],
                    metadatas=[{"source": "b.pdf", "page": 1, "chunk_id": "b::1"}])

    directory = Path(config.NOTEBOOKS_DIR) / slug
    result = notebooks.delete_notebook(slug)
    assert not directory.exists()
    assert slug not in [nb["slug"] for nb in notebooks.list_notebooks()]
    leftovers = [p.name for p in Path(config.NOTEBOOKS_DIR).glob(".trash_*")]
    return f"{result} (restes en corbeille : {leftovers or 'aucun'})"


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        config.NOTEBOOKS_DIR = Path(tmp) / "notebooks"
        test_slugs()
        print("slugs : ok")
        test_refusals(config.NOTEBOOKS_DIR)
        print("refus (hors dossier, hérités, identifiants dangereux) : ok")
        slug = notebooks.create_notebook("Essai")
        test_fake_pdf(slug)
        print("faux PDF refusés : ok")
        test_chat(slug)
        print("historique (aller-retour, Document refusé, hérité) : ok")
        result = test_create_and_delete()
        print(f"création + base Chroma réelle + suppression : ok -> {result}")
        notebooks.close_notebook(slug)
    print("\nTous les tests passent.")


if __name__ == "__main__":
    main()
