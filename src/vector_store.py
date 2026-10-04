"""Base vectorielle ChromaDB et embeddings locaux."""
import gc
from functools import lru_cache
from pathlib import Path

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src import config


@lru_cache(maxsize=1)  # le modèle est chargé UNE fois, puis partagé par toutes les bases
def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},                # le modèle est assez léger pour le CPU
        encode_kwargs={"normalize_embeddings": True},  # vecteurs de norme 1 : comparaison propre
    )


def get_vector_store(persist_dir=None) -> Chroma:
    path = Path(persist_dir) if persist_dir else config.CHROMA_DIR
    path.mkdir(parents=True, exist_ok=True)
    store = Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(path),
        # télémétrie désactivée : aucune donnée, même anonyme, ne sort de la machine
        client_settings=Settings(anonymized_telemetry=False),
    )
    store.persist_dir = str(path.resolve())  # clé du cache BM25 (src/hybrid_search.py)
    return store


def close_store(store: Chroma) -> None:
    """Libère les fichiers de la base : sous Windows, un fichier ouvert ne peut pas être supprimé."""
    store._client.close()
    gc.collect()


def delete_source(store: Chroma, source: str) -> int:
    """Supprime tout ce qui vient d'un PDF, pour réingérer sans doublons ni restes."""
    found = store.get(where={"source": source})
    if found["ids"]:
        store.delete(ids=found["ids"])
    return len(found["ids"])


def add_documents(store: Chroma, documents: list) -> None:
    if documents:
        store.add_documents(documents, ids=[d.metadata["chunk_id"] for d in documents])


def count_documents(store: Chroma) -> int:
    return store._collection.count()  # pas d'équivalent public simple dans LangChain