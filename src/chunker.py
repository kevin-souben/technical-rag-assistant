"""Découpage du texte en chunks, avec métadonnées de traçabilité."""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config
from src.pdf_extractor import PageText

MIN_CHUNK_CHARS = 30  # ignore les miettes (numéros de page, en-têtes isolés)


def chunk_pages(pages: list[PageText]) -> list[Document]:
    """Découpe chaque page séparément pour que chaque chunk garde sa page exacte."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        # essaie de couper d'abord entre paragraphes, puis entre lignes, puis entre phrases...
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = []
    for page in pages:
        counter = 0
        for piece in splitter.split_text(page.text):
            if len(piece.strip()) < MIN_CHUNK_CHARS:
                continue
            chunks.append(Document(
                page_content=piece,
                metadata={
                    "source": page.source,
                    "page": page.page,
                    "type": "text",
                    # identifiant stable : relancer l'ingestion ne créera pas de doublons
                    "chunk_id": f"{page.source}::p{page.page}::t{counter}",
                },
            ))
            counter += 1
    return chunks