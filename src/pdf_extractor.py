"""Extraction du texte (page par page) et des figures d'un PDF avec PyMuPDF."""
import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from src import config


@dataclass
class PageText:
    """Le texte d'UNE page, avec son origine exacte."""
    source: str   # nom du fichier PDF
    page: int     # numéro de page (commence à 1, comme dans un lecteur PDF)
    text: str


@dataclass
class ExtractedImage:
    """Une figure extraite, avec son origine exacte."""
    source: str
    page: int
    name: str     # nom du fichier PNG : sert aussi de citation
    path: Path
    kind: str     # "raster" (image embarquée) ou "vector" (dessin recadré)
    width: int
    height: int


def _clean_text(text: str) -> str:
    """Nettoie les espaces et sauts de ligne parasites."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_text(doc, source: str) -> list[PageText]:
    pages = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        # sort=True lit les blocs de haut en bas, de gauche à droite
        text = _clean_text(page.get_text("text", sort=True))
        if text:  # on saute les pages sans texte (pages de schéma pur, pages blanches)
            pages.append(PageText(source=source, page=page_index + 1, text=text))
    return pages


def _extract_raster_images(doc, source: str, out_dir: Path) -> list[ExtractedImage]:
    images = []
    seen_xrefs = set()  # un logo répété sur chaque page a le même identifiant : on le garde une fois

    for page_index in range(len(doc)):
        page = doc[page_index]
        for img_number, img in enumerate(page.get_images(full=True), start=1):
            xref = img[0]  # identifiant interne de l'image dans le PDF
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)

            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.width < config.MIN_IMAGE_SIZE_PX or pix.height < config.MIN_IMAGE_SIZE_PX:
                    continue  # trop petite : probablement un logo ou une icône
                if pix.n - pix.alpha >= 4:  # CMYK -> RGB pour que le PNG soit lisible partout
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)

                name = f"{Path(source).stem}_p{page_index + 1:03d}_img{img_number:02d}.png"
                path = out_dir / name
                pix.save(str(path))
                images.append(ExtractedImage(
                    source=source, page=page_index + 1, name=name, path=path,
                    kind="raster", width=pix.width, height=pix.height,
                ))
            except Exception as err:  # un format d'image exotique ne doit pas bloquer tout le PDF
                print(f"  [avertissement] image xref={xref} page {page_index + 1} ignorée : {err}")
    return images


def _extract_vector_figures(doc, source: str, out_dir: Path) -> list[ExtractedImage]:
    figures = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        drawings = page.get_drawings()  # tous les traits/formes vectoriels de la page
        if len(drawings) < config.MIN_DRAWINGS_PER_PAGE:
            continue

        page_area = page.rect.width * page.rect.height
        # cluster_drawings regroupe les traits proches en zones rectangulaires (= figures)
        clusters = page.cluster_drawings(drawings=drawings)

        candidates = [
            r for r in clusters
            if r.width >= config.MIN_FIGURE_WIDTH_PT
            and r.height >= config.MIN_FIGURE_HEIGHT_PT
            and (r.width * r.height) < 0.9 * page_area  # ignore un simple cadre de page
        ]
        candidates.sort(key=lambda r: r.width * r.height, reverse=True)

        for fig_number, rect in enumerate(candidates[:config.MAX_FIGURES_PER_PAGE], start=1):
            # petite marge autour de la figure, sans sortir de la page
            clip = pymupdf.Rect(rect.x0 - 5, rect.y0 - 5, rect.x1 + 5, rect.y1 + 5) & page.rect
            try:
                pix = page.get_pixmap(clip=clip, dpi=config.FIGURE_RENDER_DPI)
                name = f"{Path(source).stem}_p{page_index + 1:03d}_fig{fig_number:02d}.png"
                path = out_dir / name
                pix.save(str(path))
                figures.append(ExtractedImage(
                    source=source, page=page_index + 1, name=name, path=path,
                    kind="vector", width=pix.width, height=pix.height,
                ))
            except Exception as err:
                print(f"  [avertissement] figure page {page_index + 1} ignorée : {err}")
    return figures


def extract_pdf(pdf_path) -> tuple[list[PageText], list[ExtractedImage]]:
    """Point d'entrée : renvoie (textes par page, images extraites) pour un PDF."""
    pdf_path = Path(pdf_path)
    source = pdf_path.name
    out_dir = config.IMAGES_DIR / pdf_path.stem  # un sous-dossier par PDF
    out_dir.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(pdf_path) as doc:
        pages = _extract_text(doc, source)
        images = _extract_raster_images(doc, source, out_dir)
        if config.EXTRACT_VECTOR_FIGURES:
            images += _extract_vector_figures(doc, source, out_dir)

    images.sort(key=lambda im: (im.page, im.name))
    return pages, images