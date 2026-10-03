"""Test rapide : extrait un PDF et affiche ce qui a été trouvé."""
import sys
import time
from pathlib import Path

from src import config
from src.chunker import chunk_pages
from src.pdf_extractor import extract_pdf


def main():
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        pdfs = sorted(config.RAW_PDF_DIR.glob("*.pdf"))
        if not pdfs:
            print(f"Aucun PDF trouvé dans {config.RAW_PDF_DIR}")
            return
        pdf_path = pdfs[0]

    print(f"PDF testé : {pdf_path.name}")
    start = time.perf_counter()
    pages, images = extract_pdf(pdf_path)
    chunks = chunk_pages(pages)
    elapsed = time.perf_counter() - start

    print(f"Pages avec texte : {len(pages)}")
    print(f"Chunks de texte  : {len(chunks)}")
    print(f"Images raster    : {sum(1 for i in images if i.kind == 'raster')}")
    print(f"Figures vecteur  : {sum(1 for i in images if i.kind == 'vector')}")
    print(f"Temps total      : {elapsed:.1f} s")

    if chunks:
        mid = chunks[len(chunks) // 2]
        print("\n--- Exemple de chunk ---")
        print(mid.metadata)
        print(mid.page_content)

    print("\n--- 5 premières images ---")
    for im in images[:5]:
        print(f"{im.name} | page {im.page} | {im.kind} | {im.width}x{im.height}")


if __name__ == "__main__":
    main()
