"""Mode hors ligne par défaut : le modèle d'embeddings est lu depuis le cache local.

Pour télécharger un nouveau modèle (une seule fois), lancez la commande avec
RAG_ALLOW_DOWNLOAD=1, par exemple en PowerShell :
    $env:RAG_ALLOW_DOWNLOAD="1"; python -m src.ingest
"""
import os

if os.environ.get("RAG_ALLOW_DOWNLOAD") != "1":
    os.environ.setdefault("HF_HUB_OFFLINE", "1")