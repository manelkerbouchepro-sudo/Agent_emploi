"""Lit directement les pages carrières des entreprises listées dans companies.json.
Types : lever, greenhouse, smartrecruiters (API publiques, sans clé) et page (HTML générique)."""
import html as htmllib
import re
import time
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from .filters import has_any
from .util import extract_links, html_to_text, make_offer

HEADERS = {"User-Agent": "Mozilla/5.0 (agent de recherche d'emploi personnel)"}


def _get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=30, **kw)
    r.raise_for_status()
    return r


def lever(c):
    out = []
    for p in _get(f"https://api.lever.co/v0/postings/{c['slug']}", params={"mode": "json"}).json():
        cat = p.get("categories") or {}
        ts = p.get("createdAt")
        date = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat() if ts else ""
        out.append(make_offer(
            id=f"lever-{c['slug']}-{p['id']}", titre=p.get("text", ""), entreprise=c["nom"],
            lieu=cat.get("location") or "", contrat=cat.get("commitment") or "", date=date,
            description=(p.get("descriptionPlain") or "")[:4000], url=p.get("hostedUrl", ""), source="carrière"))
    return out


def greenhouse(c):
    out = []
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{c['slug']}/jobs", params={"content": "true"}).json()
    for j in data.get("jobs", []):
        out.append(make_offer(
            id=f"gh-{c['slug']}-{j['id']}", titre=j.get("title", ""), entreprise=c["nom"],
            lieu=(j.get("location") or {}).get("name", ""), date=j.get("updated_at", ""),
            description=html_to_text(htmllib.unescape(j.get("content", "")))[:4000],
            url=j.get("absolute_url", ""), source="carrière"))
    return out


def smartrecruiters(c):
    out = []
    data = _get(f"https://api.smartrecruiters.com/v1/companies/{c['slug']}/postings", params={"limit": 100}).json()
    for p in data.get("content", []):
        loc = p.get("location") or {}
        out.append(make_offer(
            id=f"sr-{c['slug']}-{p['id']}", titre=p.get("name", ""), entreprise=c["nom"],
            lieu=f"{loc.get('city', '')} {loc.get('country', '')}".strip(), date=p.get("releasedDate", ""),
            url=f"https://jobs.smartrecruiters.com/{c['slug']}/{p['id']}", source="carrière"))
    return out


def _robots_ok(url):
    try:
        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True


def parse_page_html(html, base, mots_requis, limit=40):
    """Garde les liens dont le texte ressemble à un intitulé de poste."""
    out, seen = [], set()
    for url, text in extract_links(html, base):
        t = text.lower()
        if 8 < len(text) < 150 and has_any(t, mots_requis) and url not in seen:
            seen.add(url)
            out.append((url, text))
    return out[:limit]


def page(c, cfg):
    if not _robots_ok(c["url"]):
        print(f"  ! {c['nom']} : robots.txt interdit la lecture, ignoré")
        return []
    out = []
    for url, titre in parse_page_html(_get(c["url"]).text, c["url"], cfg["mots_requis"]):
        desc = ""
        if _robots_ok(url):
            try:
                desc = html_to_text(_get(url).text)[:4000]
            except requests.RequestException:
                pass
            time.sleep(1)
        out.append(make_offer(id=url, titre=titre, entreprise=c["nom"], description=desc, url=url, source="carrière"))
    return out


def fetch_all(cfg, path="companies.json"):
    import json
    offers = []
    for c in json.load(open(path, encoding="utf-8")):
        try:
            kind = c["type"]
            res = page(c, cfg) if kind == "page" else {"lever": lever, "greenhouse": greenhouse, "smartrecruiters": smartrecruiters}[kind](c)
            print(f"  {c['nom']} : {len(res)} offres")
            offers += res
        except Exception as e:
            print(f"  ! {c['nom']} : {e}")
    return offers
