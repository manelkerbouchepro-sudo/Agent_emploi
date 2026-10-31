"""Récupère les offres via l'API Offres d'emploi v2 de France Travail (gratuite, clé requise)."""
import os
import requests

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"


def get_token():
    r = requests.post(
        TOKEN_URL,
        params={"realm": "/partenaire"},
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["FT_CLIENT_ID"],
            "client_secret": os.environ["FT_CLIENT_SECRET"],
            "scope": "api_offresdemploiv2 o2dsoffre",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def normalize(o):
    return {
        "id": o.get("id"),
        "titre": o.get("intitule", ""),
        "entreprise": (o.get("entreprise") or {}).get("nom") or "",
        "lieu": (o.get("lieuTravail") or {}).get("libelle", ""),
        "contrat": o.get("typeContrat", ""),
        "experience": o.get("experienceLibelle", ""),
        "date": o.get("dateCreation", ""),
        "description": o.get("description", ""),
        "url": (o.get("origineOffre") or {}).get("urlOrigine")
        or f"https://candidat.francetravail.fr/offres/recherche/detail/{o.get('id')}",
    }


def search(query, departement, cfg, token):
    params = {
        "motsCles": query,
        "departement": departement,
        "publieeDepuis": cfg["publiee_depuis"],
        "typeContrat": cfg["type_contrat"],
        "range": "0-49",
    }
    r = requests.get(
        SEARCH_URL, params=params, headers={"Authorization": f"Bearer {token}"}, timeout=30
    )
    if r.status_code == 204:  # aucun résultat
        return []
    r.raise_for_status()
    return [normalize(o) for o in r.json().get("resultats", [])]


def fetch_all(cfg):
    token = get_token()
    seen, offers = set(), []
    for q in cfg["requetes"]:
        for dep in cfg["departements"]:
            try:
                for o in search(q, dep, cfg, token):
                    if o["id"] not in seen:
                        seen.add(o["id"])
                        offers.append(o)
            except requests.RequestException as e:
                print(f"  ! {q} / {dep} : {e}")
    return offers
