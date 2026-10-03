"""Test de la recherche : affiche les entrées les plus proches d'une question."""
import sys

from src import config
from src.vector_store import count_documents, get_vector_store


def main():
    question = " ".join(sys.argv[1:]) or "What is the operating voltage range?"
    store = get_vector_store()
    print(f"Entrées dans la base : {count_documents(store)}")
    print(f"Question : {question}\n")

    # distance : plus elle est PETITE, plus l'entrée est proche du sens de la question
    for doc, distance in store.similarity_search_with_score(question, k=config.TOP_K):
        meta = doc.metadata
        label = meta.get("image_name", "texte")
        print(f"[{distance:.3f}] {meta['type']} | {meta['source']} | page {meta['page']} | {label}")
        print(f"    {doc.page_content[:200].replace(chr(10), ' ')}\n")


if __name__ == "__main__":
    main()
