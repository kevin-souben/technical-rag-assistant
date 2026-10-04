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

def is_degenerate(text: str) -> bool:
    """Détecte une description qui boucle : trop longue, ou presque que des mots répétés."""
    words = text.lower().split()
    if len(words) > 200:
        return True
    return len(words) >= 20 and len(set(words)) / len(words) < 0.4


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
        options={
            "temperature": 0.0,
            "num_predict": 150,      # plafond de longueur : une description ne dépasse jamais ~150 tokens
            "repeat_penalty": 1.3,   # décourage le modèle de se répéter
        },
    )
    text = response["message"]["content"].strip()
    return "" if is_degenerate(text) else text  # mieux vaut pas de description qu'une description fausse


def describe_images(images, cache_path: Path, progress=None) -> dict[str, str]:
    """Décrit toutes les figures. Le cache évite de refaire un travail déjà fait.

    progress(numéro, total), optionnel, est appelé après chaque figure."""
    cache = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        # on jette les anciennes descriptions qui bouclaient : elles seront régénérées
        cache = {name: text for name, text in cache.items() if not is_degenerate(text)}

    total = len(images)
    for number, img in enumerate(images, start=1):
        if cache.get(img.name):
            print(f"  [{number}/{total}] {img.name} (déjà décrite, cache)")
            if progress:
                progress(number, total)
            continue

        start = time.perf_counter()
        try:
            cache[img.name] = describe_image(img.path)
        except Exception as err:  # une figure en échec ne doit pas bloquer les autres
            print(f"  [{number}/{total}] {img.name} : ÉCHEC ({err})")
            if progress:
                progress(number, total)
            continue

        print(f"  [{number}/{total}] {img.name} : {time.perf_counter() - start:.1f} s")
        # sauvegarde après CHAQUE image : un Ctrl+C ne fait perdre aucun travail
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        if progress:
            progress(number, total)

    return cache