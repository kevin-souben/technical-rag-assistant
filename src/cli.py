"""Interface terminal : posez vos questions, obtenez des réponses citées.

Usage :
    python -m src.cli                                  # mode interactif
    python -m src.cli "What is the operating voltage range?"   # une seule question
"""
import argparse

from src.rag_engine import ask, check_llm, source_label
from src.vector_store import count_documents, get_vector_store


def print_report(answer) -> None:
    """Affiche les sources (construites depuis les métadonnées) et les temps."""
    print("\n")
    if not answer.hits:
        print("No passage close enough in the database: the LLM was not called.")
    elif answer.cited:
        print("Cited sources:")
        for number, doc in answer.cited:
            print(f"  [{number}] {source_label(doc)}")
            if doc.metadata.get("type") == "image":
                print(f"      image file: {doc.metadata['image_path']}")
    else:
        if not answer.refused:
            print("WARNING: the answer cites no source, do not rely on it.")
        print("Passages consulted:")
        for number, (doc, dist) in enumerate(answer.hits, start=1):
            print(f"  [{number}] {source_label(doc)} (distance {dist:.2f})")

    if answer.invalid_citations:
        print(f"WARNING: nonexistent source numbers ignored: {answer.invalid_citations}")

    if answer.unsupported:
        print("WARNING: values missing from the sources used (possible fabrication): "
              + ", ".join(answer.unsupported))

    if answer.truncated:
        print("WARNING: answer cut off (length limit reached), it may be incomplete.")

    print(f"\nTime: retrieval {answer.t_retrieval:.2f} s | "
          f"first token {answer.t_first_token:.1f} s | total {answer.t_total:.1f} s")


def run_question(question: str, store) -> None:
    # pas de streaming : un texte déjà affiché ne peut plus être retiré si le modèle se rétracte
    answer = ask(question, store)
    print(answer.text)
    print_report(answer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the technical documentation")
    parser.add_argument("question", nargs="*", help="question (otherwise: interactive mode)")
    args = parser.parse_args()

    check_llm()
    print("Loading the database and the embedding model...")
    store = get_vector_store()
    print(f"Database ready: {count_documents(store)} entries.\n")

    if args.question:
        run_question(" ".join(args.question), store)
        return

    print("Ask your question (empty, 'quit' or 'exit' to quit).")
    while True:
        question = input("\nQuestion> ").strip()
        if question.lower() in {"", "quit", "exit"}:
            break
        print()
        run_question(question, store)


if __name__ == "__main__":
    main()