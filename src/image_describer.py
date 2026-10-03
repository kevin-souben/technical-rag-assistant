"""Description des figures par un VLM local (Moondream via Ollama), avec cache."""
import json
import time
from pathlib import Path

import ollama

from src import config

PROMPT = (
    "Describe this figure from an electronic component datasheet in two short sentences. "
    "Say what it shows and quote the text labels you can clearly read. "
    "Only describe what is visible."
)


def check_ollama() -> None:
    """Vérifie qu'Ollama tourne et que le VLM est installé, avec un message clair sinon."""
    try:
        names = [m.model for m in ollama.list().models]
    except Exception:
        raise SystemExit(
            "Ollama ne répond pas. Lancez l'application Ollama (icône dans la barre des tâches), "
            "puis relancez la commande."
        )
    if not any(name.startswith(config.VLM_MODEL) for name in names):
        raise SystemExit(f"Modèle manquant. Lancez : ollama pull {config.VLM_MODEL}")


def describe_image(image_path) -> str:
    """Envoie UNE image au VLM local et renvoie sa description en texte."""
    response = ollama.chat(
        model=config.VLM_MODEL,
        messages=[{"role": "user", "content": PROMPT, "images": [str(image_path)]}],
        options={"temperature": 0.0},  # 0 = réponse la plus stable, pas de créativité
    )
    return response["message"]["content"].strip()


def describe_images(images, cache_path: Path) -> dict[str, str]:
    """Décrit toutes les figures. Le cache évite de refaire un travail déjà fait."""
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))

    total = len(images)
    for number, img in enumerate(images, start=1):
        if cache.get(img.name):
            print(f"  [{number}/{total}] {img.name} (déjà décrite, cache)")
            continue

        start = time.perf_counter()
        try:
            cache[img.name] = describe_image(img.path)
        except Exception as err:  # une figure en échec ne doit pas bloquer les autres
            print(f"  [{number}/{total}] {img.name} : ÉCHEC ({err})")
            continue

        print(f"  [{number}/{total}] {img.name} : {time.perf_counter() - start:.1f} s")
        # sauvegarde après CHAQUE image : un Ctrl+C ne fait perdre aucun travail
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    return cache