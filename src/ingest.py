"""Pipeline d'ingestion : PDF -> texte + figures -> chunks -> embeddings -> ChromaDB.

Usage :
    python -m src.ingest                      # tous les PDF de data/raw_pdfs
    python -m src.ingest fichier.pdf          # un PDF précis
    python -m src.ingest --no-images          # saute le VLM (rapide, pour tester)
"""
import argparse
import time
from pathlib import Path

from langchain_core.documents import Document

from src import config
from src.chunker import chunk_pages
from src.image_describer import check_ollama, describe_images
from src.pdf_extractor import ExtractedImage, extract_pdf
from src.vector_store import add_documents, count_documents, delete_source, get_vector_store


def image_to_document(img: ExtractedImage, description: str, page_context: str = "") -> Document:
    """Transforme une figure en document indexable : contexte de page + description du VLM + texte natif."""
    parts = [f"Figure {img.name} (page {img.page})."]
    if page_context:
        parts.append(f"Page context: {page_context}")  # en premier : l'embedding lit surtout le début
    if description:
        parts.append(description)
    if img.text:
        labels = " | ".join(line for line in img.text.splitlines() if line.strip())
        parts.append(f"Text found in the figure: {labels}")
    return Document(
        page_content="\n".join(parts),
        metadata={
            "source": img.source,
            "page": img.page,
            "type": "image",
            "image_name": img.name,
            "image_path": str(img.path),
            "chunk_id": f"{img.source}::p{img.page}::{img.name}",
        },
    )


def ingest_pdf(pdf_path: Path, store, with_images: bool = True) -> None:
    print(f"\n=== {pdf_path.name} ===")

    t0 = time.perf_counter()
    pages, images = extract_pdf(pdf_path)
    text_chunks = chunk_pages(pages)
    t_extract = time.perf_counter() - t0
    print(f"Extraction : {len(pages)} pages, {len(text_chunks)} chunks, "
          f"{len(images)} figures ({t_extract:.1f} s)")

    descriptions = {}
    t_vlm = 0.0
    if with_images and images:
        print("Description des figures par le VLM local :")
        t1 = time.perf_counter()
        cache_path = config.IMAGES_DIR / pdf_path.stem / "descriptions.json"
        descriptions = describe_images(images, cache_path)
        t_vlm = time.perf_counter() - t1

    # début du texte de chaque page (titre de section) : sert de contexte aux figures
    page_starts = {p.page: " ".join(p.text.split())[:200] for p in pages}

    image_docs = []
    for img in images:
        description = descriptions.get(img.name, "")
        if description or img.text:  # une figure sans aucun texte n'est pas cherchable
            context = page_starts.get(img.page, "")
            image_docs.append(image_to_document(img, description, context))

    t2 = time.perf_counter()
    removed = delete_source(store, pdf_path.name)  # réingestion propre
    add_documents(store, text_chunks + image_docs)
    t_index = time.perf_counter() - t2

    if removed:
        print(f"{removed} anciennes entrées de ce PDF remplacées")
    print(f"Indexé : {len(text_chunks)} chunks texte + {len(image_docs)} figures")
    print(f"Temps : extraction {t_extract:.1f} s | VLM {t_vlm:.1f} s | indexation {t_index:.1f} s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingestion de PDF techniques dans ChromaDB")
    parser.add_argument("pdfs", nargs="*", help="PDF à ingérer (défaut : data/raw_pdfs/*.pdf)")
    parser.add_argument("--no-images", action="store_true", help="ne pas appeler le VLM")
    args = parser.parse_args()

    pdf_paths = [Path(p) for p in args.pdfs] or sorted(config.RAW_PDF_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"Aucun PDF trouvé dans {config.RAW_PDF_DIR}")

    with_images = not args.no_images
    if with_images:
        check_ollama()

    print("Chargement du modèle d'embeddings (1er lancement : téléchargement unique)...")
    store = get_vector_store()

    for pdf_path in pdf_paths:
        ingest_pdf(pdf_path, store, with_images)

    print(f"\nTerminé. Total dans la base : {count_documents(store)} entrées.")


if __name__ == "__main__":
    main()