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
        print("Aucun passage assez proche dans la base : le LLM n'a pas été appelé.")
    elif answer.cited:
        print("Sources citées :")
        for number, doc in answer.cited:
            print(f"  [{number}] {source_label(doc)}")
            if doc.metadata.get("type") == "image":
                print(f"      fichier image : {doc.metadata['image_path']}")
    else:
        if not answer.refused:
            print("ATTENTION : la réponse ne cite aucune source, ne pas s'y fier.")
        print("Passages consultés :")
        for number, (doc, dist) in enumerate(answer.hits, start=1):
            print(f"  [{number}] {source_label(doc)} (distance {dist:.2f})")

    if answer.invalid_citations:
        print(f"ATTENTION : numéros de source inexistants ignorés : {answer.invalid_citations}")

    if answer.unsupported:
        print("ATTENTION : valeurs absentes des sources utilisées (possible invention) : "
              + ", ".join(answer.unsupported))

    print(f"\nTemps : recherche {answer.t_retrieval:.2f} s | "
          f"1er mot {answer.t_first_token:.1f} s | total {answer.t_total:.1f} s")


def run_question(question: str, store) -> None:
    answer = ask(question, store, on_token=lambda t: print(t, end="", flush=True))
    if not answer.hits:
        print(answer.text, end="")  # pas de streaming dans ce cas : on affiche le refus
    print_report(answer)


def main() -> None:
    parser = argparse.ArgumentParser(description="Interrogation de la documentation technique")
    parser.add_argument("question", nargs="*", help="question (sinon : mode interactif)")
    args = parser.parse_args()

    check_llm()
    print("Chargement de la base et du modèle d'embeddings...")
    store = get_vector_store()
    print(f"Base prête : {count_documents(store)} entrées.\n")

    if args.question:
        run_question(" ".join(args.question), store)
        return

    print("Posez votre question (vide, 'quit' ou 'exit' pour quitter).")
    while True:
        question = input("\nQuestion> ").strip()
        if question.lower() in {"", "quit", "exit"}:
            break
        print()
        run_question(question, store)


if __name__ == "__main__":
    main()