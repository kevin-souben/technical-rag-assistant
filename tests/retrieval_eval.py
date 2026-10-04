"""Mesure de la recherche SEULE (sans LLM) : la page attendue est-elle retrouvée ?

Usage :
    python -m tests.retrieval_eval

Pour chaque question, on regarde :
  - le rang de la première entrée dont la page est attendue (parmi les WIDE_K plus proches,
    sans seuil de distance) ;
  - si la page attendue est dans ce que le LLM reçoit réellement (TOP_K + seuil de distance) ;
  - pour les questions hors sujet : si elles sont bloquées avant le LLM.
La mesure est au niveau de la PAGE, pas du passage : elle peut être légèrement optimiste.
"""
import json
from datetime import date
from pathlib import Path

from src import config
from src.rag_engine import retrieve
from src.vector_store import count_documents, get_vector_store

QUESTIONS_FILE = Path(__file__).parent / "benchmark_questions.json"
OUTPUT_FILE = config.BASE_DIR / "docs" / "retrieval_baseline.md"
WIDE_K = 20  # profondeur d'observation, au-delà de TOP_K, pour voir où se classe la bonne page


def measure(item: dict, store) -> dict:
    """Lance la recherche pour UNE question et renvoie ce qu'on veut observer."""
    question = item["question"]
    wide = store.similarity_search_with_score(question, k=WIDE_K)
    context = retrieve(store, question)  # exactement ce que le LLM recevrait
    expected = set(item["expected_pages"])

    first_rank, first_distance = None, None
    for rank, (doc, distance) in enumerate(wide, start=1):
        if doc.metadata["page"] in expected:
            first_rank, first_distance = rank, distance
            break

    context_pages = {doc.metadata["page"] for doc, _ in context}
    return {
        "id": item["id"],
        "should_refuse": item["should_refuse"],
        "expected": sorted(expected),
        "first_rank": first_rank,
        "first_distance": first_distance,
        "context_pages": sorted(context_pages),
        "any_in_context": bool(expected & context_pages),
        "all_in_context": bool(expected) and expected <= context_pages,
        "blocked": len(context) == 0,
        # signature : sert à vérifier que deux exécutions donnent exactement le même résultat
        "signature": [(doc.metadata["chunk_id"], round(d, 5)) for doc, d in wide],
    }


def main() -> None:
    items = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    store = get_vector_store()

    first_pass = [measure(item, store) for item in items]
    second_pass = [measure(item, store) for item in items]
    deterministic = all(a["signature"] == b["signature"] for a, b in zip(first_pass, second_pass))

    answerable = [r for r in first_pass if not r["should_refuse"]]
    refusals = [r for r in first_pass if r["should_refuse"]]

    lines = [
        f"Retrieval only (no LLM), {len(items)} questions, {count_documents(store)} indexed entries, "
        f"embedding `{config.EMBEDDING_MODEL}`, top-K {config.TOP_K}, "
        f"distance threshold {config.MAX_DISTANCE}, {date.today()}",
        "",
        f"Observation depth: {WIDE_K} nearest entries. Measured at page level, not passage level.",
        "",
        "| ID | Expected page(s) | Rank of first expected page | Distance | Expected page in LLM context | Pages in LLM context |",
        "|---|---|---|---|---|---|",
    ]
    for r in first_pass:
        if r["should_refuse"]:
            outcome = "blocked before LLM" if r["blocked"] else "NOT blocked"
            lines.append(f"| {r['id']} | none (refusal expected) | - | - | {outcome} | "
                         f"{', '.join(map(str, r['context_pages'])) or 'none'} |")
            continue
        rank = str(r["first_rank"]) if r["first_rank"] else f"> {WIDE_K}"
        distance = f"{r['first_distance']:.2f}" if r["first_distance"] is not None else "-"
        lines.append(f"| {r['id']} | {', '.join(map(str, r['expected']))} | {rank} | {distance} | "
                     f"{'yes' if r['any_in_context'] else 'no'} | "
                     f"{', '.join(map(str, r['context_pages'])) or 'none'} |")

    n = len(answerable)
    lines += [
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Answerable questions with an expected page in the LLM context | "
        f"{sum(r['any_in_context'] for r in answerable)}/{n} |",
        f"| Answerable questions with ALL expected pages in the LLM context | "
        f"{sum(r['all_in_context'] for r in answerable)}/{n} |",
        f"| Answerable questions with an expected page in the {WIDE_K} nearest entries | "
        f"{sum(r['first_rank'] is not None for r in answerable)}/{n} |",
        f"| Off-topic questions blocked before the LLM | "
        f"{sum(r['blocked'] for r in refusals)}/{len(refusals)} |",
        f"| Identical results over two runs | {'yes' if deterministic else 'NO'} |",
    ]

    report = "\n".join(lines)
    print(report)
    OUTPUT_FILE.write_text(report + "\n", encoding="utf-8")
    print(f"\nEnregistré dans {OUTPUT_FILE}")


if __name__ == "__main__":
    main()