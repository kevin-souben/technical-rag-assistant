"""Interface web locale : une question -> réponse citée + schémas cités affichés.

Lancement :  streamlit run src/app_streamlit.py
"""
import sys
from pathlib import Path

# Streamlit exécute ce fichier depuis src/ : on ajoute la racine du projet
# pour que "from src import ..." fonctionne.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src.rag_engine import ask, check_llm, source_label
from src.vector_store import count_documents, get_vector_store

st.set_page_config(page_title="Technical RAG Assistant", page_icon="🔧", layout="wide")


@st.cache_resource(show_spinner="Loading the database and the embedding model...")
def load_store():
    """Chargé UNE fois : Streamlit relance le script à chaque interaction."""
    return get_vector_store()


st.title("🔧 Technical RAG Assistant")
st.caption("Technical documentation queried 100% locally: no data leaves this machine.")

try:
    check_llm()
except SystemExit as err:  # message clair si Ollama est éteint ou le modèle absent
    st.error(str(err))
    st.stop()

store = load_store()
st.sidebar.metric("Indexed entries", count_documents(store))
st.sidebar.caption("Example questions:")
st.sidebar.code("What is the operating voltage range of the ESP32?\nWhat are the strapping pins of the ESP32?")

question = st.chat_input("Ask your question (in English for now)")

if question:
    st.markdown(f"**Question:** {question}")

    with st.spinner("Retrieving and generating locally..."):
        answer = ask(question, store)

    # --- Réponse ---
    if answer.refused:
        st.warning(answer.text)
    else:
        st.markdown(answer.text)

    # --- Avertissements de fiabilité ---
    if not answer.hits:
        st.info("No passage close enough in the database: the LLM was not called.")
    elif not answer.refused and not answer.cited:
        st.error("The answer cites no source: do not rely on it.")
    if answer.invalid_citations:
        st.error(f"Nonexistent source numbers ignored: {answer.invalid_citations}")
    if answer.unsupported:
        st.error("Values missing from the sources used (possible fabrication): "
                 + ", ".join(answer.unsupported))
    if answer.truncated:
        st.warning("Answer cut off (length limit reached): it may be incomplete.")

    # --- Sources citées, avec les schémas affichés ---
    if answer.cited:
        st.subheader("Cited sources")
        for number, doc in answer.cited:
            st.markdown(f"**[{number}]** `{source_label(doc)}`")
            if doc.metadata.get("type") == "image":
                image_path = Path(doc.metadata["image_path"])
                if image_path.exists():
                    st.image(str(image_path), caption=doc.metadata["image_name"], width=700)
                else:
                    st.caption(f"Image not found: {image_path}")

    # --- Tous les passages donnés au LLM ---
    if answer.hits:
        with st.expander(f"Passages consulted ({len(answer.hits)})"):
            for number, (doc, dist) in enumerate(answer.hits, start=1):
                st.markdown(f"**[{number}]** `{source_label(doc)}` (distance {dist:.2f})")
                st.text(doc.page_content[:400])

    st.caption(f"Retrieval {answer.t_retrieval:.2f} s | first token {answer.t_first_token:.1f} s | "
               f"total {answer.t_total:.1f} s")