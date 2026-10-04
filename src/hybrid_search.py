"""Recherche hybride : embeddings (sens) + BM25 (mots exacts), fusionnés par RRF.

Le BM25 est écrit à la main (une trentaine de lignes) : pas de dépendance en plus,
et la formule reste explicable en entretien.
"""
import math
import re
from collections import Counter

from langchain_core.documents import Document

from src import config
from src.vector_store import count_documents

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
QUERY_ID_RE = re.compile(r"\b[A-Z][A-Z0-9_]{3,}\b")  # SPICLK, HSPIQ, GPIO12... (4 caractères min.)
BM25_K1 = 1.5   # saturation de la fréquence d'un mot (valeur standard)
BM25_B = 0.75   # normalisation par la longueur du passage (valeur standard)
RRF_K = 60      # constante standard de la fusion RRF


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


class BM25Index:
    """Classe les passages selon les mots exacts de la question."""

    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.tokens = [tokenize(d.page_content) for d in docs]
        self.n = len(docs)
        self.avg_len = sum(len(t) for t in self.tokens) / max(self.n, 1)
        self.tf = [Counter(t) for t in self.tokens]   # fréquence de chaque mot, par passage
        self.df = Counter()                           # nombre de passages contenant chaque mot
        for tokens in self.tokens:
            self.df.update(set(tokens))

    def idf(self, term: str) -> float:
        """Poids d'un mot : élevé s'il est rare, faible s'il est partout."""
        n_t = self.df.get(term, 0)
        return math.log(1 + (self.n - n_t + 0.5) / (n_t + 0.5))

    def scores(self, query: str) -> list[float]:
        terms = set(tokenize(query))
        result = [0.0] * self.n
        for i, tf in enumerate(self.tf):
            length = len(self.tokens[i])
            for term in terms:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                denominator = f + BM25_K1 * (1 - BM25_B + BM25_B * length / self.avg_len)
                result[i] += self.idf(term) * f * (BM25_K1 + 1) / denominator
        return result


_cache = {"count": None, "index": None}


def get_index(store) -> BM25Index:
    """Construit l'index BM25 depuis ChromaDB, et le reconstruit si la base a changé."""
    count = count_documents(store)
    if _cache["count"] != count:
        data = store.get(include=["documents", "metadatas"])
        docs = [Document(page_content=text, metadata=meta)
                for text, meta in zip(data["documents"], data["metadatas"])]
        _cache["count"], _cache["index"] = count, BM25Index(docs)
    return _cache["index"]


def rank_candidates(store, question: str) -> list[tuple]:
    """Classement fusionné [(doc, distance, score RRF)], SANS aucun filtre.

    Corpus petit (quelques centaines d'entrées) : on demande la distance de TOUTES
    les entrées. Pour un corpus beaucoup plus grand, il faudrait limiter ce nombre.
    """
    index = get_index(store)
    dense = store.similarity_search_with_score(question, k=index.n)
    bm25 = index.scores(question)
    order = sorted((i for i in range(index.n) if bm25[i] > 0), key=lambda i: bm25[i], reverse=True)
    sparse_rank = {index.docs[i].metadata["chunk_id"]: r for r, i in enumerate(order, start=1)}

    fused = []
    for dense_rank, (doc, distance) in enumerate(dense, start=1):
        chunk_id = doc.metadata["chunk_id"]
        score = 1 / (RRF_K + dense_rank)
        if chunk_id in sparse_rank:
            score += 1 / (RRF_K + sparse_rank[chunk_id])
        fused.append((doc, distance, score))
    fused.sort(key=lambda item: item[2], reverse=True)
    return fused


def rare_query_identifiers(index: BM25Index, question: str) -> set[str]:
    """Identifiants en majuscules de la question qui existent dans le corpus ET y sont rares."""
    rare = set()
    for token in QUERY_ID_RE.findall(question):
        df = index.df.get(token.lower(), 0)
        if 0 < df <= config.RARE_DF_RATIO * index.n:
            rare.add(token.lower())
    return rare


def hybrid_retrieve(store, question: str) -> list[tuple]:
    """Ce que le LLM reçoit : [(doc, distance)], au plus TOP_K passages.

    Un passage est gardé s'il est assez proche (seuil de distance) OU s'il contient
    un identifiant rare de la question (porte lexicale).
    """
    index = get_index(store)
    rare = rare_query_identifiers(index, question)
    kept = []
    for doc, distance, _ in rank_candidates(store, question):
        lexical_match = bool(rare & set(tokenize(doc.page_content)))
        if distance <= config.MAX_DISTANCE or lexical_match:
            kept.append((doc, distance))
        if len(kept) == config.TOP_K:
            break
    return kept