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


@st.cache_resource(show_spinner="Chargement de la base et du modèle d'embeddings...")
def load_store():
    """Chargé UNE fois : Streamlit relance le script à chaque interaction."""
    return get_vector_store()


st.title("🔧 Technical RAG Assistant")
st.caption("Documentation technique interrogée 100 % en local : aucune donnée ne quitte cette machine.")

try:
    check_llm()
except SystemExit as err:  # message clair si Ollama est éteint ou le modèle absent
    st.error(str(err))
    st.stop()

store = load_store()
st.sidebar.metric("Entrées indexées", count_documents(store))
st.sidebar.caption("Exemples de questions :")
st.sidebar.code("What is the operating voltage range of the ESP32?\nWhat are the strapping pins of the ESP32?")

question = st.chat_input("Posez votre question (en anglais pour l'instant)")

if question:
    st.markdown(f"**Question :** {question}")

    with st.spinner("Recherche et génération en local..."):
        answer = ask(question, store)

    # --- Réponse ---
    if answer.refused:
        st.warning(answer.text)
    else:
        st.markdown(answer.text)

    # --- Avertissements de fiabilité ---
    if not answer.hits:
        st.info("Aucun passage assez proche dans la base : le LLM n'a pas été appelé.")
    elif not answer.refused and not answer.cited:
        st.error("La réponse ne cite aucune source : ne pas s'y fier.")
    if answer.invalid_citations:
        st.error(f"Numéros de source inexistants ignorés : {answer.invalid_citations}")
    if answer.unsupported:
        st.error("Valeurs absentes des sources utilisées (possible invention) : "
                 + ", ".join(answer.unsupported))
    if answer.truncated:
        st.warning("Réponse coupée (limite de longueur atteinte) : elle peut être incomplète.")

    # --- Sources citées, avec les schémas affichés ---
    if answer.cited:
        st.subheader("Sources citées")
        for number, doc in answer.cited:
            st.markdown(f"**[{number}]** `{source_label(doc)}`")
            if doc.metadata.get("type") == "image":
                image_path = Path(doc.metadata["image_path"])
                if image_path.exists():
                    st.image(str(image_path), caption=doc.metadata["image_name"], width=700)
                else:
                    st.caption(f"Image introuvable : {image_path}")

    # --- Tous les passages donnés au LLM ---
    if answer.hits:
        with st.expander(f"Passages consultés ({len(answer.hits)})"):
            for number, (doc, dist) in enumerate(answer.hits, start=1):
                st.markdown(f"**[{number}]** `{source_label(doc)}` (distance {dist:.2f})")
                st.text(doc.page_content[:400])

    st.caption(f"Recherche {answer.t_retrieval:.2f} s | 1er mot {answer.t_first_token:.1f} s | "
               f"total {answer.t_total:.1f} s")