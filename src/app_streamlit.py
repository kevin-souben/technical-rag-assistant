"""Interface web locale : plusieurs notebooks, chacun avec ses sources et son historique.

Lancement :  streamlit run src/app_streamlit.py

Streamlit relance ce script en entier à chaque clic : tout l'état durable est sur le disque
(src/notebooks.py), st.session_state ne garde que le notebook sélectionné et des messages.
Une base ne s'ouvre QUE par notebooks.open_store(), pour que delete_notebook() puisse la fermer.
"""
import re
import sys
from pathlib import Path

# Streamlit exécute ce fichier depuis src/ : on ajoute la racine du projet
# pour que "from src import ..." fonctionne.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from src import notebooks
from src.rag_engine import ask, check_llm, source_label
from src.ui_style import apply_style

# erreurs prévues du backend : affichées avec st.error, jamais de plantage
NOTEBOOK_ERRORS = (ValueError, PermissionError, RuntimeError, FileNotFoundError)
DEFAULT_SLUG = "esp32"
RECENT_COUNT = 10
# avertissements affichés en jaune ; tous les autres en rouge
MILD_WARNINGS = ("No passage close enough", "Answer cut off")
# messages de progression envoyés par src/ingest.py (en français) -> (fraction, texte affiché)
PROGRESS_STEPS = {
    "Extraction du texte et des figures": (0.05, "extracting text and figures"),
    "Indexation (embeddings)": (0.90, "indexing (embeddings)"),
    "Terminé": (1.0, "done"),
}

st.set_page_config(page_title="Technical RAG Assistant", page_icon=":material/menu_book:",
                   layout="centered")
apply_style()

try:
    check_llm()
except SystemExit as err:  # message clair si Ollama est éteint ou le modèle absent
    st.error(str(err))
    st.stop()

st.session_state.setdefault("slug", DEFAULT_SLUG)
st.session_state.setdefault("flash", [])       # messages à afficher après un st.rerun()
st.session_state.setdefault("uploader_n", 0)   # changer la clé vide le champ d'envoi de fichiers


def select_notebook(slug: str) -> None:
    st.session_state.slug = slug


def ask_again(question: str) -> None:
    st.session_state.pending_question = question


def progress_step(message: str, previous: float) -> tuple[float, str]:
    """Traduit un message de progression de l'ingestion en (fraction, texte en anglais)."""
    figures = re.search(r"(\d+)/(\d+)", message)  # "Description des figures : 3/12"
    if figures:
        done, total = int(figures.group(1)), int(figures.group(2))
        return 0.10 + 0.80 * done / max(total, 1), f"describing figures {done}/{total}"
    return PROGRESS_STEPS.get(message, (previous, message))


def render_entry(entry: dict, hits=None) -> None:
    """Affiche UN échange depuis le dictionnaire de make_chat_entry : historique et réponse du moment.

    hits (réponse du moment seulement, jamais stocké) ajoute la liste des passages consultés."""
    with st.chat_message("user"):
        st.markdown(entry["question"])
    with st.chat_message("assistant"):
        if entry["refused"]:
            st.warning(entry["answer"])
        else:
            st.markdown(entry["answer"])

        for warning in entry["warnings"]:
            if warning.startswith(MILD_WARNINGS):
                st.warning(warning)
            else:
                st.error(warning)

        if entry["cited"]:
            st.markdown("**Cited sources**")
            for cited in entry["cited"]:
                st.markdown(f"**[{cited['number']}]** `{cited['label']}`")
                if cited["image_path"]:
                    image_path = Path(cited["image_path"])
                    if image_path.exists():
                        st.image(str(image_path), caption=image_path.name)
                    else:
                        st.caption(f"Image not found: {image_path}")

        if hits:
            with st.expander(f"Passages consulted ({len(hits)})"):
                for number, (doc, dist) in enumerate(hits, start=1):
                    st.markdown(f"**[{number}]** `{source_label(doc)}` (distance {dist:.2f})")
                    st.text(doc.page_content[:400])

        t = entry["timings"]
        st.caption(f"Retrieval {t['retrieval']:.2f} s | first token {t['first_token']:.1f} s | "
                   f"total {t['total']:.1f} s")


# --- Barre latérale : liste des notebooks et création ---
try:
    all_notebooks = notebooks.list_notebooks()
except NOTEBOOK_ERRORS as err:
    st.error(f"Could not list the notebooks: {err}")
    st.stop()

by_slug = {nb["slug"]: nb for nb in all_notebooks}
if st.session_state.slug not in by_slug:  # notebook supprimé entre-temps
    st.session_state.slug = DEFAULT_SLUG
slug = st.session_state.slug
notebook = by_slug[slug]

st.sidebar.title("Notebooks")
for nb in all_notebooks:
    st.sidebar.button(
        nb["name"], key=f"select_{nb['slug']}", width="stretch",
        type="primary" if nb["slug"] == slug else "secondary",
        icon=":material/lock:" if nb["legacy"] else ":material/description:",
        on_click=select_notebook, args=(nb["slug"],),
    )

st.sidebar.subheader("New notebook")
with st.sidebar.form("new_notebook", clear_on_submit=True, border=False):
    new_name = st.text_input("Name", placeholder="e.g. Motherboard manual")
    create = st.form_submit_button("Create", width="stretch")
if create:
    try:
        st.session_state.slug = notebooks.create_notebook(new_name)
        st.rerun()
    except NOTEBOOK_ERRORS as err:
        st.sidebar.error(str(err))

# --- Zone centrale ---
st.title(notebook["name"])

for kind, text in st.session_state.flash:
    getattr(st, kind)(text)
st.session_state.flash = []

try:
    with st.spinner("Loading the database and the embedding model..."):
        store = notebooks.open_store(slug)
    sources = notebooks.list_sources(slug)
except NOTEBOOK_ERRORS as err:
    st.error(str(err))
    st.stop()

# --- Sources ---
st.subheader("Sources")
if notebook["legacy"]:
    st.caption("Protected notebook (used for the published measurements)")
if not sources:
    st.caption("No source yet. Add a PDF below.")
for source in sources:
    left, right = st.columns([5, 1], vertical_alignment="center")
    left.markdown(f"`{source['source']}` · {source['entries']} entries")
    if not notebook["legacy"]:
        with right.popover("Remove", width="stretch"):
            st.write(f"Remove **{source['source']}** from this notebook? "
                     "Its entries, the PDF file and its figures are deleted.")
            if st.button("Confirm removal", key=f"remove_{source['source']}", type="primary"):
                try:
                    removed = notebooks.remove_source(slug, source["source"])
                    st.session_state.flash.append(
                        ("success", f"{source['source']} removed ({removed} entries)."))
                except NOTEBOOK_ERRORS as err:
                    st.session_state.flash.append(("error", str(err)))
                st.rerun()

if not notebook["legacy"]:
    with st.expander("Add sources"):
        files = st.file_uploader("PDF files", type=["pdf"], accept_multiple_files=True,
                                 key=f"uploader_{slug}_{st.session_state.uploader_n}")
        with_images = st.checkbox("Describe figures with the vision model (slower)", value=True,
                                  key=f"with_images_{slug}")
        if st.button("Add", type="primary", disabled=not files, key=f"add_{slug}"):
            results = []
            for uploaded in files:
                bar = st.progress(0.0, text=f"{uploaded.name}: starting")
                state = {"value": 0.0}

                def on_progress(message, bar=bar, name=uploaded.name, state=state):
                    state["value"], text = progress_step(message, state["value"])
                    bar.progress(state["value"], text=f"{name}: {text}")

                try:
                    count = notebooks.add_pdf(slug, uploaded.getvalue(), uploaded.name,
                                              with_images, progress=on_progress)
                    results.append(("success", f"{uploaded.name}: {count} entries indexed."))
                except NOTEBOOK_ERRORS as err:
                    results.append(("error", f"{uploaded.name}: {err}"))
                except Exception as err:  # l'ingestion (PyMuPDF, Chroma) peut lever d'autres erreurs
                    results.append(("error", f"{uploaded.name}: {type(err).__name__}: {err}"))
            st.session_state.flash.extend(results)
            st.session_state.uploader_n += 1  # vide le champ d'envoi
            st.rerun()

    with st.expander("Danger zone"):
        st.write(f"Deleting **{notebook['name']}** is permanent: its database, PDF files, "
                 "figures and history are all removed.")
        typed = st.text_input("Type the notebook name to confirm", key=f"confirm_delete_{slug}")
        if st.button("Delete notebook", type="primary", disabled=typed != notebook["name"],
                     key=f"delete_{slug}"):
            try:
                result = notebooks.delete_notebook(slug)
                message = f"Notebook {notebook['name']!r}: {result}."
                if result == "trashed":
                    message += " Some files were still locked; they will be purged at the next start."
                st.session_state.flash.append(("success", message))
                st.session_state.slug = DEFAULT_SLUG
            except NOTEBOOK_ERRORS as err:
                st.session_state.flash.append(("error", str(err)))
            st.rerun()

# --- Conversation ---
st.divider()
try:
    history = notebooks.load_chat(slug)
except NOTEBOOK_ERRORS as err:
    st.error(f"Could not read the history: {err}")
    history = []

if history:
    with st.sidebar.popover("Clear history", width="stretch"):
        st.write("Delete the history of this notebook only? Its sources are kept.")
        if st.button("Confirm", key=f"clear_{slug}", type="primary"):
            try:
                notebooks.clear_chat(slug)
            except NOTEBOOK_ERRORS as err:
                st.session_state.flash.append(("error", str(err)))
            st.rerun()
st.caption("Each question is answered on its own: the assistant has no memory of earlier "
           "messages, the history below is only displayed.")

for entry in history:
    render_entry(entry)

question = st.chat_input("Ask your question (in English for now)")
if not question:
    question = st.session_state.pop("pending_question", None)  # clic dans "Recent"

if question:
    with st.spinner("Retrieving and generating locally..."):
        answer = ask(question, store)
    entry = notebooks.make_chat_entry(question, answer)
    try:
        notebooks.append_chat(slug, entry)
        history.append(entry)
    except NOTEBOOK_ERRORS as err:
        st.error(f"The answer could not be saved in the history: {err}")
    render_entry(entry, hits=answer.hits)

# --- Barre latérale, en dernier : la question qu'on vient de poser y figure déjà ---
st.sidebar.subheader("Recent")
if not history:
    st.sidebar.caption("No question yet in this notebook.")
for entry in reversed(history[-RECENT_COUNT:]):
    st.sidebar.button(entry["question"], key=f"recent_{entry['id']}", type="tertiary",
                      width="stretch", on_click=ask_again, args=(entry["question"],))
