"""Recherche web via l'outil de recherche intégré à l'API Claude (pas de scraping de sites interdits)."""
import json
import os

from .util import make_offer

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """Tu cherches des offres d'emploi réelles sur le web pour une candidate junior.
Règles strictes : ne retourne QUE des offres que tu as réellement vues dans les résultats de recherche,
avec leur vrai lien. N'invente jamais un lien, une date ou une entreprise. Exclus les ESN, stages et alternances.
Réponds uniquement par un tableau JSON :
[{"titre":"","entreprise":"","lieu":"","url":"","date":"AAAA-MM-JJ ou vide","extrait":""}]"""


def search_web(query, max_uses=4):
    from anthropic import Anthropic
    client = Anthropic()
    msg = client.messages.create(
        model=MODEL, max_tokens=3000, system=SYSTEM,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": max_uses}],
        messages=[{"role": "user", "content": query}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end < 0:
        return []
    return [make_offer(id=o["url"], titre=o.get("titre", ""), entreprise=o.get("entreprise", ""),
                       lieu=o.get("lieu", ""), date=o.get("date", ""), description=o.get("extrait", ""),
                       url=o["url"], source="recherche web")
            for o in json.loads(text[start:end + 1]) if o.get("url")]


def fetch_all(cfg):
    from .targets import web_queries
    offers = []
    queries = list(cfg.get("requetes_web", []))
    # recherches ciblées sur les entreprises A puis B de ta liste (cibles.json)
    queries += web_queries(cfg.get("cibles", []), max_queries=cfg.get("recherche_web_cibles", 8))
    for q in queries:
        try:
            res = search_web(q)
            print(f"  « {q} » : {len(res)} offres")
            offers += res
        except Exception as e:
            print(f"  ! recherche web « {q} » : {e}")
    return offers
