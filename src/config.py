"""Configuration centrale du projet : chemins, modèles et paramètres.

Tout ce qu'on peut vouloir régler se trouve ici, jamais dans le reste du code.
"""
from pathlib import Path

# --- Chemins (calculés depuis l'emplacement de ce fichier) ---
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PDF_DIR = BASE_DIR / "data" / "raw_pdfs"
IMAGES_DIR = BASE_DIR / "data" / "extracted_images"
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"

# --- Extraction des images raster ---
MIN_IMAGE_SIZE_PX = 150  # ignore les images plus petites (logos, puces)

# --- Extraction des figures vectorielles ---
EXTRACT_VECTOR_FIGURES = True
MIN_DRAWINGS_PER_PAGE = 15      # nombre minimal de traits sur la page pour chercher des figures
MIN_FIGURE_WIDTH_PT = 150       # 1 point = 1/72 pouce
MIN_FIGURE_HEIGHT_PT = 100
MAX_FIGURES_PER_PAGE = 4        # évite d'inonder le VLM sur les pages de tableaux
FIGURE_RENDER_DPI = 150         # résolution du rendu PNG

# --- Chunking du texte ---
CHUNK_SIZE = 700       # caractères (~180 tokens) : tient dans la limite du modèle d'embedding
CHUNK_OVERLAP = 120    # chevauchement pour ne pas couper une phrase importante

# --- Modèles (utilisés à l'étape 3b et 4) ---
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VLM_MODEL = "moondream"
LLM_MODEL = "llama3.2:3b"
COLLECTION_NAME = "technical_docs"
TOP_K = 5