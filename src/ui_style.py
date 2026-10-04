"""Style de l'interface : CSS injecté dans la page Streamlit (les couleurs sont dans .streamlit/config.toml)."""
import streamlit as st

# Les data-testid viennent de Streamlit 1.64 : ils peuvent changer avec une autre version.
CSS = """
<style>
/* contenu centré, largeur limitée : plus facile à lire */
[data-testid="stMainBlockContainer"] { max-width: 800px; padding-top: 2rem; }
/* titre du notebook centré */
h1 { text-align: center; font-weight: 500; }
/* champ de saisie arrondi */
[data-testid="stChatInput"], [data-testid="stChatInput"] > div { border-radius: 24px; }
[data-testid="stChatInput"] textarea { padding-left: 0.5rem; }
/* menu, bouton de déploiement et pied de page de Streamlit masqués */
[data-testid="stMainMenu"], [data-testid="stAppDeployButton"], footer { display: none; }
/* boutons de la barre latérale alignés à gauche, comme une liste */
[data-testid="stSidebar"] button { justify-content: flex-start; text-align: left; }
/* bouton de confirmation (popover) de la barre latérale : texte centré comme les autres boutons */
[data-testid="stSidebar"] [data-testid="stPopover"] button { justify-content: center; text-align: center; }
[data-testid="stSidebar"] [data-testid="stPopover"] button > div { justify-content: center; }
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
