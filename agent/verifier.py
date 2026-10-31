"""Vérifie qu'une offre existe encore (évite les liens morts)."""
import requests

DEAD = ("n'existe plus", "n’existe plus", "plus disponible", "offre expirée",
        "a été pourvue", "offre pourvue", "no longer available", "position has been filled")


def is_alive(url):
    """True = vivante, False = morte, None = impossible à savoir."""
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
    except requests.RequestException:
        return None
    if r.status_code in (404, 410):
        return False
    if r.status_code >= 400:
        return None
    text = r.text.lower()
    return not any(m in text for m in DEAD)
