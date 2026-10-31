"""Mémorise les offres déjà présentées pour ne montrer que les nouvelles à chaque lancement."""
import json
import os
from datetime import date

PATH = "deja_vues.json"


def _key(o):
    return o.get("url") or f"{o['titre'].lower().strip()}|{o['entreprise'].lower().strip()}"


def load(path=PATH):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def split_new(offers, seen):
    new, old = [], []
    for o in offers:
        (old if _key(o) in seen else new).append(o)
    return new, old


def remember(offers, seen, path=PATH):
    today = str(date.today())
    for o in offers:
        seen.setdefault(_key(o), today)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=0)
    os.replace(tmp, path)
