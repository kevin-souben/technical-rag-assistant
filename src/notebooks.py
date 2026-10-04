"""Notebooks : des collections de documents indépendantes (base, PDF, images, historique).

Un notebook = un dossier data/notebooks/<slug>/ :
    chroma_db/   base vectorielle propre au notebook
    pdfs/        PDF ajoutés
    images/      figures extraites (un sous-dossier par PDF)
    chats.json   historique des échanges (affichage seulement : le LLM n'en a aucune mémoire)
    meta.json    nom affiché et date de création

Les bases existantes (esp32, msi) sont des notebooks "hérités" : interrogeables, mais
protégés (ni suppression, ni ajout, ni retrait de PDF). Leur historique est rangé dans
data/notebooks/_legacy_chats/, jamais dans leurs dossiers.

Sécurité : toute écriture ou suppression passe par _check_inside(), qui refuse
une cible hors de config.NOTEBOOKS_DIR ou dans une base protégée.
"""
import json
import os
import re
import shutil
import unicodedata
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import pymupdf

from src import config
from src.hybrid_search import forget_index
from src.image_describer import check_ollama
from src.ingest import ingest_pdf
from src.rag_engine import source_label
from src.vector_store import close_store, delete_source, get_vector_store

SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
MAX_SLUG_LEN = 40
LEGACY_CHATS = "_legacy_chats"
RESERVED = {"esp32", "msi", LEGACY_CHATS}
MAX_PDF_BYTES = 200 * 1024 * 1024        # 200 Mo
FORBIDDEN_NAME_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')  # caractères interdits ou dangereux sous Windows
WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
CHAT_KEYS = {"id", "timestamp", "question", "answer", "refused", "truncated",
             "warnings", "cited", "timings"}

_stores = {}       # slug -> base Chroma ouverte (pour pouvoir la fermer avant suppression)
_started = False   # la corbeille est purgée une fois, avant la première ouverture de base


# --- Chemins et sécurité ---

def _data_dir() -> Path:
    return config.BASE_DIR / "data"


def _protected_dirs() -> list[Path]:
    """Dossiers qu'aucune opération de ce module ne doit jamais toucher."""
    data = _data_dir()
    dirs = [data / "chroma_db", data / "raw_pdfs", data / "extracted_images"]
    dirs += [p for p in data.glob("chroma_db_*")]
    return [d.resolve() for d in dirs]


def _check_inside(path) -> Path:
    """Renvoie le chemin résolu s'il est DANS config.NOTEBOOKS_DIR (et hors des bases protégées).

    resolve() suit les liens et les "..", donc "notebooks/../chroma_db" est bien refusé."""
    root = Path(config.NOTEBOOKS_DIR).resolve()
    target = Path(path).resolve()
    if target == root or root not in target.parents:
        raise PermissionError(f"Refusé : {target} n'est pas dans {root}")
    for protected in _protected_dirs():
        if target == protected or protected in target.parents:
            raise PermissionError(f"Refusé : {target} est une base protégée")
    return target


def _legacy() -> dict:
    """Notebooks hérités : chemins fixes (pas config.CHROMA_DIR, qui dépend de RAG_DB)."""
    data = _data_dir()
    legacy = {"esp32": {"name": "ESP32", "chroma_dir": data / "chroma_db",
                        "images_dir": data / "extracted_images"}}
    if (data / "chroma_db_msi").exists():
        legacy["msi"] = {"name": "MSI", "chroma_dir": data / "chroma_db_msi",
                         "images_dir": data / "extracted_images"}
    return legacy


def validate_slug(slug) -> str:
    """Minuscules, chiffres et tirets, 40 caractères maximum, pas un nom réservé."""
    if not isinstance(slug, str) or not slug or len(slug) > MAX_SLUG_LEN:
        raise ValueError(f"Identifiant invalide : {slug!r}")
    if not SLUG_RE.fullmatch(slug):  # exclut ".", "..", "/", "\\", majuscules, espaces
        raise ValueError(f"Identifiant invalide : {slug!r}")
    if slug in RESERVED:
        raise ValueError(f"Identifiant réservé : {slug!r}")
    return slug


def slugify(name: str) -> str:
    """'Carte mère MSI' -> 'carte-mere-msi'."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug[:MAX_SLUG_LEN].rstrip("-")


def _notebook_dir(slug: str) -> Path:
    """Dossier d'un notebook créé par l'utilisateur (refuse les hérités et les inconnus)."""
    if slug in _legacy():
        raise PermissionError(f"Le notebook {slug!r} est protégé")
    validate_slug(slug)
    directory = Path(config.NOTEBOOKS_DIR) / slug
    _check_inside(directory)
    if not (directory / "meta.json").exists():
        raise ValueError(f"Notebook inconnu : {slug!r}")
    return directory


def _paths(slug: str) -> dict:
    """Chemins utiles d'un notebook, hérité ou non."""
    legacy = _legacy()
    if slug in legacy:
        return {**legacy[slug], "legacy": True,
                "chat_file": Path(config.NOTEBOOKS_DIR) / LEGACY_CHATS / f"{slug}.json"}
    directory = _notebook_dir(slug)
    return {"chroma_dir": directory / "chroma_db", "images_dir": directory / "images",
            "pdfs_dir": directory / "pdfs", "chat_file": directory / "chats.json",
            "legacy": False}


def _write_json(path: Path, obj) -> None:
    """Écriture atomique : un fichier à moitié écrit (coupure) ne remplace jamais l'ancien."""
    _check_inside(path)
    tmp = path.with_name(path.name + ".tmp")
    _check_inside(tmp)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _clean_pdf_name(filename) -> str:
    """Garde le seul nom du fichier (aucun dossier) et exige l'extension .pdf."""
    name = Path(str(filename).replace("\\", "/")).name
    stem = Path(name).stem
    if (not name or name in {".", ".."} or FORBIDDEN_NAME_CHARS.search(name)
            or Path(name).suffix.lower() != ".pdf"  # ".pdf" seul : suffixe vide, refusé
            or not stem.strip(". ")                 # "..pdf" : un nom fait uniquement de points
            or stem.split(".")[0].upper() in WINDOWS_RESERVED):  # CON.pdf, NUL.pdf...
        raise ValueError(f"Nom de PDF invalide : {filename!r}")
    return name


def _check_pdf_bytes(data) -> None:
    if not isinstance(data, bytes):
        raise ValueError("Le contenu du PDF doit être des octets")
    if len(data) > MAX_PDF_BYTES:
        raise ValueError(f"PDF trop gros : {len(data) / 1e6:.0f} Mo (maximum 200 Mo)")
    if not data.startswith(b"%PDF"):
        raise ValueError("Ce fichier n'est pas un PDF (il ne commence pas par %PDF)")
    # ouverture EN MÉMOIRE : un faux PDF est refusé avant d'écrire quoi que ce soit sur le disque
    # (sous Windows, un fichier que PyMuPDF n'a pas réussi à ouvrir reste verrouillé)
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            if doc.page_count == 0:
                raise ValueError("PDF sans aucune page")
    except ValueError:
        raise
    except Exception as err:
        raise ValueError(f"PDF illisible : {err}") from err


# --- Corbeille (Windows : Chroma peut garder ses fichiers ouverts) ---

def purge_trash() -> int:
    """Supprime les dossiers .trash_* laissés par une suppression qui avait échoué."""
    root = Path(config.NOTEBOOKS_DIR)
    if not root.exists():
        return 0
    purged = 0
    for directory in root.iterdir():
        if directory.is_dir() and directory.name.startswith(".trash_"):
            shutil.rmtree(_check_inside(directory), ignore_errors=True)
            purged += not directory.exists()
    return purged


def _startup() -> None:
    global _started
    if not _started:
        purge_trash()  # AVANT d'ouvrir une base
        _started = True


# --- Notebooks ---

def list_notebooks() -> list[dict]:
    """Notebooks hérités d'abord, puis ceux de l'utilisateur par date de création."""
    _startup()
    result = [{"slug": slug, "name": info["name"], "created": None, "legacy": True,
               "chroma_dir": str(info["chroma_dir"]), "images_dir": str(info["images_dir"])}
              for slug, info in _legacy().items()]
    root = Path(config.NOTEBOOKS_DIR)
    user = []
    if root.exists():
        for directory in root.iterdir():
            meta_file = directory / "meta.json"
            if (directory.is_dir() and SLUG_RE.fullmatch(directory.name)
                    and directory.name not in RESERVED and meta_file.exists()):
                meta = json.loads(meta_file.read_text(encoding="utf-8"))
                user.append({"slug": directory.name, "name": meta["name"],
                             "created": meta["created"], "legacy": False,
                             "chroma_dir": str(directory / "chroma_db"),
                             "images_dir": str(directory / "images")})
    return result + sorted(user, key=lambda nb: nb["created"])


def create_notebook(name: str) -> str:
    """Crée le dossier du notebook et renvoie son identifiant (slug)."""
    name = (name or "").strip()
    slug = validate_slug(slugify(name))
    directory = Path(config.NOTEBOOKS_DIR) / slug
    _check_inside(directory)
    if directory.exists():
        raise ValueError(f"Un notebook {slug!r} existe déjà")
    for sub in ("chroma_db", "pdfs", "images"):
        (directory / sub).mkdir(parents=True)
    _write_json(directory / "meta.json",
                {"name": name, "created": datetime.now().isoformat(timespec="seconds")})
    _write_json(directory / "chats.json", [])
    return slug


def open_store(slug: str):
    """Base Chroma du notebook, ouverte une seule fois puis réutilisée."""
    _startup()
    if slug in _stores:
        return _stores[slug]
    paths = _paths(slug)
    if paths["legacy"]:
        if not paths["chroma_dir"].exists():  # get_vector_store créerait un dossier dans data/
            raise FileNotFoundError(f"Base introuvable : {paths['chroma_dir']}")
    else:
        _check_inside(paths["chroma_dir"])
    _stores[slug] = get_vector_store(paths["chroma_dir"])
    return _stores[slug]


def close_notebook(slug: str) -> None:
    """Ferme la base (libère ses fichiers) et oublie son index BM25."""
    store = _stores.pop(slug, None)
    if store is not None:
        close_store(store)
        forget_index(store.persist_dir)


def delete_notebook(slug: str) -> str:
    """Supprime un notebook. Renvoie "deleted", ou "trashed" s'il a fallu passer par la corbeille."""
    directory = _check_inside(_notebook_dir(slug))
    close_notebook(slug)
    forget_index((directory / "chroma_db").resolve())
    try:
        shutil.rmtree(directory)
        return "deleted"
    except OSError:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        trash = _check_inside(Path(config.NOTEBOOKS_DIR) / f".trash_{slug}_{stamp}")
        try:
            directory.rename(trash)
        except OSError as err:
            raise RuntimeError(f"Suppression impossible ({err}) : fermez l'application, "
                               "puis réessayez.") from err
        shutil.rmtree(trash, ignore_errors=True)  # le reste sera purgé au prochain démarrage
        return "trashed"


# --- Sources (PDF) ---

def add_pdf(slug: str, data: bytes, filename: str, with_images: bool, progress=None) -> int:
    """Ajoute (ou remplace) un PDF dans un notebook. Renvoie le nombre d'entrées indexées."""
    paths = _paths(slug)
    if paths["legacy"]:
        raise PermissionError(f"Le notebook {slug!r} est protégé")
    name = _clean_pdf_name(filename)
    _check_pdf_bytes(data)
    if with_images:
        try:
            check_ollama()  # avant d'écrire quoi que ce soit
        except SystemExit as err:  # l'interface doit pouvoir afficher le message, pas fermer le programme
            raise RuntimeError(str(err)) from None

    pdf_path = _check_inside(paths["pdfs_dir"] / name)
    _check_inside(paths["images_dir"])
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(data)

    store = open_store(slug)
    count = ingest_pdf(pdf_path, store, with_images, images_dir=paths["images_dir"],
                       progress=progress)
    forget_index(store.persist_dir)
    return count


def remove_source(slug: str, source: str) -> int:
    """Retire un PDF : ses entrées dans la base, le fichier et ses figures. Renvoie le nombre d'entrées retirées."""
    paths = _paths(slug)
    if paths["legacy"]:
        raise PermissionError(f"Le notebook {slug!r} est protégé")
    name = _clean_pdf_name(source)
    pdf_path = _check_inside(paths["pdfs_dir"] / name)
    images = _check_inside(paths["images_dir"] / Path(name).stem)

    store = open_store(slug)
    removed = delete_source(store, name)
    forget_index(store.persist_dir)
    if pdf_path.exists():
        pdf_path.unlink()
    if images.exists():
        shutil.rmtree(images)
    return removed


def list_sources(slug: str) -> list[dict]:
    """PDF présents dans la base (d'après les métadonnées Chroma) et leur nombre d'entrées."""
    data = open_store(slug).get(include=["metadatas"])
    counts = Counter(meta["source"] for meta in data["metadatas"])
    return [{"source": source, "entries": n} for source, n in sorted(counts.items())]


# --- Historique (stocké pour l'affichage ; jamais renvoyé au LLM) ---

def make_chat_entry(question: str, answer) -> dict:
    """Convertit une Answer en dictionnaire de textes et de nombres (aucun objet Document)."""
    warnings = []
    if not answer.hits:
        warnings.append("No passage close enough in the database: the LLM was not called.")
    elif not answer.refused and not answer.cited:
        warnings.append("The answer cites no source: do not rely on it.")
    if answer.invalid_citations:
        warnings.append(f"Nonexistent source numbers ignored: {answer.invalid_citations}")
    if answer.unsupported:
        warnings.append("Values missing from the sources used (possible fabrication): "
                        + ", ".join(answer.unsupported))
    if answer.truncated:
        warnings.append("Answer cut off (length limit reached): it may be incomplete.")
    return {
        "id": uuid.uuid4().hex,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "question": question,
        "answer": answer.text,
        "refused": answer.refused,
        "truncated": answer.truncated,
        "warnings": warnings,
        "cited": [{"number": number, "label": source_label(doc),
                   "image_path": doc.metadata.get("image_path")}
                  for number, doc in answer.cited],
        "timings": {"retrieval": answer.t_retrieval, "first_token": answer.t_first_token,
                    "total": answer.t_total},
    }


def load_chat(slug: str) -> list[dict]:
    chat_file = _paths(slug)["chat_file"]
    if not chat_file.exists():
        return []
    return json.loads(chat_file.read_text(encoding="utf-8"))


def append_chat(slug: str, entry: dict) -> None:
    """Ajoute un échange. Refuse une entrée incomplète ou non sérialisable (ex. un Document)."""
    if not isinstance(entry, dict) or set(entry) != CHAT_KEYS:
        raise ValueError(f"Entrée d'historique invalide, clés attendues : {sorted(CHAT_KEYS)}")
    try:
        json.dumps(entry)
    except TypeError as err:  # un Document n'est pas sérialisable en JSON
        raise ValueError(f"Entrée d'historique non sérialisable : {err}") from err
    _write_json(_paths(slug)["chat_file"], load_chat(slug) + [entry])


def clear_chat(slug: str) -> None:
    _write_json(_paths(slug)["chat_file"], [])
