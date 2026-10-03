"""Benchmark : pose chaque question N fois et mesure justesse, citations, avertissements, latence.

Usage :
    python -m tests.benchmark                    # 3 essais par question, modèle de config.py
    python -m tests.benchmark --runs 1           # test rapide
    python -m tests.benchmark --model mistral    # comparer un autre LLM
"""
import argparse
import json
import re
import statistics
import time
from collections import Counter
from datetime import date
from pathlib import Path

from src import config
from src.rag_engine import ask, check_llm
from src.vector_store import count_documents, get_vector_store

QUESTIONS_FILE = Path(__file__).parent / "benchmark_questions.json"
RESULTS_DIR = config.BASE_DIR / "docs"
WARMUP_QUESTION = "What is the operating voltage range of the ESP32?"


def contains_term(text: str, term: str) -> bool:
    """Cherche un terme exact : 'GPIO1' ne doit pas être trouvé dans 'GPIO12'."""
    pattern = r"(?<![\w.])" + re.escape(term) + r"(?!\d)"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def evaluate(item: dict, answer) -> dict:
    """Classe UNE réponse dans une catégorie et note la page citée."""
    warned = bool(answer.unsupported or answer.invalid_citations) or (
        not answer.refused and not answer.cited
    )
    cited_pages = sorted({doc.metadata["page"] for _, doc in answer.cited})

    if item["should_refuse"]:
        correct = answer.refused
        page_ok = None
    else:
        terms_ok = all(contains_term(answer.text, t) for t in item["expected_all"])
        no_forbidden = not any(contains_term(answer.text, t) for t in item.get("forbidden", []))
        correct = (not answer.refused) and terms_ok and no_forbidden
        page_ok = bool(set(cited_pages) & set(item["expected_pages"])) if correct else None

    if correct:
        category = "ok"
    elif answer.refused:
        category = "refusal_wrong"   # sûr mais inutile : la réponse existait
    elif warned:
        category = "error_flagged"   # réponse fausse, mais le système l'a signalée
    else:
        category = "error_silent"    # réponse fausse SANS avertissement : le cas dangereux

    return {
        "category": category,
        "page_ok": page_ok,
        "cited_pages": cited_pages,
        "warned": warned,
        "answer": answer.text,
        "unsupported": answer.unsupported,
        "t_retrieval": answer.t_retrieval,
        "t_first_token": answer.t_first_token,
        "t_total": answer.t_total,
        "llm_called": bool(answer.hits),
    }


def median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark du moteur RAG")
    parser.add_argument("--runs", type=int, default=3, help="essais par question (défaut : 3)")
    parser.add_argument("--model", help="LLM Ollama à tester (défaut : config.LLM_MODEL)")
    args = parser.parse_args()

    if args.model:
        config.LLM_MODEL = args.model
    check_llm()

    items = json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))
    store = get_vector_store()
    print(f"Modèle : {config.LLM_MODEL} | base : {count_documents(store)} entrées | "
          f"{len(items)} questions x {args.runs} essais\n")

    # Échauffement : le 1er appel charge le LLM en mémoire, on le mesure à part
    t0 = time.perf_counter()
    ask(WARMUP_QUESTION, store)
    load_time = time.perf_counter() - t0
    print(f"Échauffement (chargement du LLM) : {load_time:.1f} s\n")

    results = []
    for item in items:
        runs = [evaluate(item, ask(item["question"], store)) for _ in range(args.runs)]
        results.append({"item": item, "runs": runs})
        counts = Counter(r["category"] for r in runs)
        summary = ", ".join(f"{cat} x{n}" for cat, n in counts.items())
        print(f"[{item['id']}] {item['question'][:55]:<55} | {summary} | "
              f"{median([r['t_total'] for r in runs]):.1f} s")

    # --- Agrégats ---
    all_runs = [r for res in results for r in res["runs"]]
    total = len(all_runs)
    counts = Counter(r["category"] for r in all_runs)
    answered_ok = [r for r in all_runs if r["category"] == "ok" and r["page_ok"] is not None]
    llm_runs = [r for r in all_runs if r["llm_called"]]
    unstable = [res["item"]["id"] for res in results
                if len({r["category"] for r in res["runs"]}) > 1]

    def pct(n: int, d: int) -> str:
        return f"{100 * n / d:.0f} % ({n}/{d})" if d else "n/a"

    rows = [
        ("Correct answers or correct refusals", pct(counts["ok"], total)),
        ("Silent errors (wrong, no warning)", pct(counts["error_silent"], total)),
        ("Flagged errors (wrong, warning shown)", pct(counts["error_flagged"], total)),
        ("Useless refusals (answer existed)", pct(counts["refusal_wrong"], total)),
        ("Correct page cited (among correct answers)",
         pct(sum(1 for r in answered_ok if r["page_ok"]), len(answered_ok))),
        ("Unstable questions (verdict changes between runs)", f"{len(unstable)}/{len(items)}"),
        ("Median total latency (LLM called)", f"{median([r['t_total'] for r in llm_runs]):.1f} s"),
        ("Median first token (LLM called)", f"{median([r['t_first_token'] for r in llm_runs]):.1f} s"),
        ("Max total latency", f"{max((r['t_total'] for r in all_runs), default=0):.1f} s"),
        ("Median retrieval", f"{median([r['t_retrieval'] for r in all_runs]) * 1000:.0f} ms"),
        ("First LLM load", f"{load_time:.1f} s"),
    ]
    header = (f"Model `{config.LLM_MODEL}`, {len(items)} questions x {args.runs} runs, "
              f"top-K {config.TOP_K}, distance threshold {config.MAX_DISTANCE}, {date.today()}")
    markdown = f"{header}\n\n| Metric | Result |\n|---|---|\n" + \
        "\n".join(f"| {name} | {value} |" for name, value in rows)

    print("\n" + markdown)
    if unstable:
        print(f"\nQuestions instables : {', '.join(unstable)}")

    # --- Sauvegarde (les réponses complètes permettent de relire chaque erreur) ---
    RESULTS_DIR.mkdir(exist_ok=True)
    safe_model = re.sub(r"[^\w.-]", "_", config.LLM_MODEL)
    json_path = RESULTS_DIR / f"benchmark_{safe_model}.json"
    json_path.write_text(json.dumps(
        {"model": config.LLM_MODEL, "runs_per_question": args.runs, "load_time_s": load_time,
         "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULTS_DIR / f"benchmark_{safe_model}.md").write_text(markdown + "\n", encoding="utf-8")
    print(f"\nRésultats enregistrés dans {json_path}")


if __name__ == "__main__":
    main()