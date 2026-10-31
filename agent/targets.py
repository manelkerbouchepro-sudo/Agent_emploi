"""Liste d'entreprises cibles : import depuis le fichier Excel, priorité, et repérage dans les offres.

Priorité :
  A = Grand Est (Nancy, Metz, Strasbourg) ou industrie / automobile / ferroviaire / énergie,
      là où ton expérience Emotors compte le plus
  B = éditeurs de logiciels, startups tech et IA (Paris surtout)
  C = défense (sites ZRR), laboratoires de recherche, intégrateurs en agences, matériel quantique
Les ESN et cabinets de conseil sont écartés (esn_blacklist de config.json + quelques cabinets).
"""
import json
import re
import unicodedata

VILLES = ["Nancy / Metz", "Strasbourg", "Paris / Île-de-France"]  # ordre = ordre d'affichage
GRAND_EST = ("Nancy / Metz", "Strasbourg")
DOMAINES = ["Génie logiciel", "Intelligence artificielle / Data", "Électronique & systèmes embarqués",
            "Automatisme / Automatique", "Mécatronique", "Robotique"]
CONSEIL = ["accenture", "ekimetrics", "artefact"]

INDUSTRIE = re.compile(r"auto|ferroviaire|industri|énergie|electri|électri|automati|puissance|PLM|"
                       r"actionneur|moteur(?!s? de recherche)|transmission|machines|capteurs|électrovannes|motoréducteur|mécatroni|équipementier", re.I)
C_ACTIVITE = re.compile(r"(?<!moteur de )recherche|intégrateur|quantique|laboratoire", re.I)


def norm(name):
    """Nom simplifié pour comparer : sans accents, sans « (ex-...) », sans suffixes courants."""
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(group|groupe|france|sas|sa|se|inc|ltd|gmbh)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def is_esn(name, cfg):
    n = (name or "").lower()
    return any(re.search(r"(?<![\w])" + re.escape(b) + r"(?![\w])", n)
               for b in cfg["esn_blacklist"] + CONSEIL)


def priority(ville, tag, activite):
    tag = tag or ""
    if "Militaire" in tag:
        return "C", "Défense : sites souvent classés ZRR, procédure longue"
    if C_ACTIVITE.search(activite or ""):
        if ville in GRAND_EST:
            return "B", "Grand Est, mais recherche / agence d'intégration"
        return "C", "Recherche, intégrateur en agences ou matériel de pointe"
    if ville in GRAND_EST:
        return "A", "Grand Est, proche de chez toi"
    if INDUSTRIE.search(activite or ""):
        return "A", "Industrie / automobile / énergie : ton expérience Emotors compte"
    return "B", "Éditeur ou startup tech / IA"


def from_rows(rows, cfg):
    """rows : lignes de l'onglet « Toutes » (Domaine, Entreprise, Tag, Ville, Site, Activité, Site web...).
    Renvoie une entrée par (entreprise, ville), domaines regroupés, ESN retirées, triée par priorité."""
    agg = {}
    for r in rows:
        dom, nom, tag, ville, site, act, web = (list(r) + [None] * 7)[:7]
        if not nom or ville not in VILLES or dom not in DOMAINES or is_esn(nom, cfg):
            continue
        e = agg.setdefault((nom, ville), {"nom": nom, "tag": tag or "", "ville": ville, "site": site or "",
                                           "activite": act or "", "web": web or "", "domaines": []})
        short = dom.split(" / ")[0].replace(" & systèmes embarqués", "")
        if short not in e["domaines"]:
            e["domaines"].append(short)
    out = []
    for e in agg.values():
        e["priorite"], e["pourquoi"] = priority(e["ville"], e["tag"], e["activite"])
        out.append(e)
    order = {"A": 0, "B": 1, "C": 2}
    out.sort(key=lambda e: (order[e["priorite"]], VILLES.index(e["ville"]), e["nom"].lower()))
    return out


def load(path="cibles.json"):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def index(cibles):
    """{nom normalisé: meilleure priorité}."""
    idx = {}
    for c in cibles:
        k = norm(c["nom"])
        if k and (k not in idx or c["priorite"] < idx[k]):
            idx[k] = c["priorite"]
    return idx


def match(entreprise, idx):
    """Priorité de l'entreprise si elle est dans ta liste, sinon None.
    « Valeo Comfort and Driving Assistance » est reconnue comme « Valeo »."""
    n = norm(entreprise)
    if not n:
        return None
    if n in idx:
        return idx[n]
    best = None
    for k, p in idx.items():
        if len(k) >= 4 and (n.startswith(k + " ") or k.startswith(n + " ")):
            best = p if best is None or p < best else best
    return best


def web_queries(cibles, max_queries=8, par_requete=4):
    """Requêtes de recherche web ciblées sur les entreprises A, puis B, groupées par ville."""
    queries = []
    for prio in ("A", "B"):
        for ville in VILLES:
            noms = [c["nom"] for c in cibles if c["priorite"] == prio and c["ville"] == ville]
            for i in range(0, len(noms), par_requete):
                groupe = " OR ".join('"' + re.sub(r"\s*\(.*?\)", "", n) + '"' for n in noms[i:i + par_requete])
                lieu = ville.split(" / ")[0] if ville != "Nancy / Metz" else "Nancy OR Metz"
                queries.append(f"offre emploi CDI développeur OR ingénieur logiciel junior {groupe} {lieu} 2026")
    return queries[:max_queries]
