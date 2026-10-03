"""Base vectorielle ChromaDB et embeddings locaux."""
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from src import config


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},                # le modèle est assez léger pour le CPU
        encode_kwargs={"normalize_embeddings": True},  # vecteurs de norme 1 : comparaison propre
    )


def get_vector_store() -> Chroma:
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=config.COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(config.CHROMA_DIR),
        # télémétrie désactivée : aucune donnée, même anonyme, ne sort de la machine
        client_settings=Settings(anonymized_telemetry=False),
    )


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