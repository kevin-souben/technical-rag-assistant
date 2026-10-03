"""Moteur RAG : recherche -> prompt contraint -> LLM local -> réponse avec citations vérifiées."""
import re
import time
from dataclasses import dataclass, field

import ollama

from src import config

NOT_FOUND = "Not found in the provided documents."

SYSTEM_PROMPT = (
    "You are a technical assistant for hardware and embedded engineers. "
    "Answer ONLY using the numbered sources provided by the user.\n"
    "Rules:\n"
    "1. Cite every factual statement with its source number in square brackets, like [1] or [2][3]. "
    "Cite a source only if it actually contains that statement.\n"
    "2. Never use outside knowledge. Never invent values, pin numbers, or units.\n"
    f"3. If the sources do not contain the answer, your entire reply must be exactly: {NOT_FOUND} "
    "Add nothing else: no explanation and no partial answer.\n"
    "4. Copy numbers, units, and pin names exactly as written in the sources.\n"
    "5. When a source lists several parameters that answer the question "
    "(for example several supply voltages), report all of them with symbol, min, typ, max and unit.\n"
    "6. Figure descriptions written by a small vision model can be inaccurate: "
    "prefer the 'Text found in the figure' lines.\n"
    "7. Answer in the language of the question, keeping technical terms as in the source. "
    "Be concise."
)


@dataclass
class Answer:
    text: str
    hits: list = field(default_factory=list)       # [(Document, distance)] donnés au LLM
    cited: list = field(default_factory=list)      # [(numéro, Document)] réellement cités
    invalid_citations: list = field(default_factory=list)
    unsupported: list = field(default_factory=list)  # valeurs de la réponse absentes des sources
    refused: bool = False
    t_retrieval: float = 0.0
    t_first_token: float = 0.0
    t_total: float = 0.0


def check_llm() -> None:
    """Vérifie qu'Ollama tourne et que le LLM est installé."""
    try:
        names = [m.model for m in ollama.list().models]
    except Exception:
        raise SystemExit(
            "Ollama ne répond pas. Lancez l'application Ollama, puis relancez la commande."
        )
    if not any(name.startswith(config.LLM_MODEL) for name in names):
        raise SystemExit(f"Modèle manquant. Lancez : ollama pull {config.LLM_MODEL}")


def source_label(doc) -> str:
    """Référence lisible d'un passage : fichier, page, et nom du schéma si c'en est un."""
    m = doc.metadata
    if m.get("type") == "image":
        return f"{m['source']} | page {m['page']} | figure {m['image_name']}"
    return f"{m['source']} | page {m['page']} | text"


def retrieve(store, question: str) -> list:
    """Cherche les TOP_K passages les plus proches, puis écarte ceux qui sont trop éloignés."""
    results = store.similarity_search_with_score(question, k=config.TOP_K)
    return [(doc, dist) for doc, dist in results if dist <= config.MAX_DISTANCE]


def build_context(hits: list) -> str:
    """Numérote les passages : [1], [2]... Le LLM ne cite que ces numéros."""
    parts = []
    for number, (doc, _) in enumerate(hits, start=1):
        parts.append(f"[{number}] ({source_label(doc)})\n{doc.page_content}")
    return "\n\n".join(parts)


def extract_citations(text: str, n_sources: int) -> tuple[list[int], list[int]]:
    """Trouve les [n] dans la réponse. Renvoie (numéros valides, numéros inventés)."""
    numbers = []
    for group in re.findall(r"\[([\d,\s]+)\]", text):  # accepte [1], [2][3] et [1, 2]
        for part in group.split(","):
            if part.strip().isdigit():
                numbers.append(int(part.strip()))
    valid = sorted({n for n in numbers if 1 <= n <= n_sources})
    invalid = sorted({n for n in numbers if not 1 <= n <= n_sources})
    return valid, invalid

# Ce qu'on vérifie : broches (GPIO12), valeurs avec unité (3.6V, 80 MHz)
# et valeurs relatives à une tension (0.75×VIO)
VALUE_PATTERN = re.compile(
    r"GPIO\d+"
    r"|\b\d+(?:\.\d+)?\s?(?:mV|V|mA|µA|uA|A|MHz|kHz|GHz|Mbps|dBm|°C|KB|MB|ns|µs|us|ms)\b"
    r"|\b\d+(?:\.\d+)?\s?[x×]\s?[A-Z]{2,}[A-Z0-9_]*\b"
)


def find_unsupported_values(answer_text: str, source_text: str) -> list[str]:
    """Liste les broches et valeurs citées dans la réponse mais ABSENTES des sources.

    C'est une vérification lexicale : elle attrape les numéros inventés,
    pas les erreurs de raisonnement."""
    answer_clean = re.sub(r"\[[\d,\s]+\]", "", answer_text)  # on retire les [1], [2]...
    unsupported = []
    for token in VALUE_PATTERN.findall(answer_clean):
        if token.startswith("GPIO"):
            pattern = r"\b" + token + r"\b"
        else:
            number = re.match(r"\d+(?:\.\d+)?", token).group()
            pattern = r"(?<![\d.])" + re.escape(number) + r"(?!\d)"
        if not re.search(pattern, source_text) and token not in unsupported:
            unsupported.append(token)
    return unsupported


def ask(question: str, store, on_token=None) -> Answer:
    """Pipeline complet pour UNE question. on_token(str) permet d'afficher en direct."""
    t0 = time.perf_counter()
    hits = retrieve(store, question)
    t_retrieval = time.perf_counter() - t0

    if not hits:  # rien d'assez proche : inutile (et risqué) d'appeler le LLM
        return Answer(text=NOT_FOUND, refused=True, t_retrieval=t_retrieval,
                      t_total=time.perf_counter() - t0)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"Sources:\n{build_context(hits)}\n\nQuestion: {question}\n\n"
            "Reminder: put the source number, like [1], after every statement. "
            f"If the answer is not in the sources, reply exactly: {NOT_FOUND}"
        )},
    ]

    text, t_first = "", 0.0
    stream = ollama.chat(
        model=config.LLM_MODEL,
        messages=messages,
        stream=True,
        options={"temperature": config.LLM_TEMPERATURE, "num_ctx": config.LLM_NUM_CTX},
    )
    for chunk in stream:
        token = chunk["message"]["content"]
        if token and not t_first:
            t_first = time.perf_counter() - t0
        text += token
        if on_token:
            on_token(token)
    text = text.strip()

    refused = NOT_FOUND.lower() in text.lower()
    if refused:
        text = NOT_FOUND  # une réponse "à moitié refusée" n'est pas fiable : on garde le refus seul
    cited, invalid, unsupported = [], [], []
    if not refused:
        valid_numbers, invalid = extract_citations(text, len(hits))
        cited = [(n, hits[n - 1][0]) for n in valid_numbers]
        # on vérifie contre les sources citées ; sans citation, contre tous les passages
        checked_docs = [doc for _, doc in cited] or [doc for doc, _ in hits]
        source_text = "\n".join(doc.page_content for doc in checked_docs)
        unsupported = find_unsupported_values(text, source_text)

    return Answer(text=text, hits=hits, cited=cited, invalid_citations=invalid,
                  unsupported=unsupported, refused=refused, t_retrieval=t_retrieval,
                  t_first_token=t_first, t_total=time.perf_counter() - t0)