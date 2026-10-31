"""Filtres à règles : ESN, intitulé, lieu, ancienneté, niveau d'expérience."""
import re
from datetime import datetime, timezone

EXP_RE = re.compile(r"(\d+)\s*(?:à\s*\d+\s*)?ans?\s+d['’]?\s*exp", re.I)


def has_word(text, word):
    """True si `word` apparaît comme mot entier (« ia » ne matche pas « commercial »).
    Gère les mots avec ponctuation comme « c# » ou « .net »."""
    return re.search(r"(?<![\w])" + re.escape(word.lower()) + r"(?![\w#+])", text.lower()) is not None


def has_any(text, words):
    return any(has_word(text, w) for w in words)


def age_days(date_iso):
    if not date_iso:
        return None
    try:
        d = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d).days
    except ValueError:
        return None


def experience_required(offer):
    """Renvoie le nombre d'années demandé si on peut le lire, sinon None."""
    text = f"{offer['titre']} {offer['experience']} {offer['description']}"
    if "débutant" in offer["experience"].lower():
        return 0
    nums = [int(m.group(1)) for m in EXP_RE.finditer(text)]
    nums += [int(n) for n in re.findall(r"(\d+)\s*an", offer["experience"].lower())]
    return min(nums) if nums else None


def keep(offer, cfg):
    titre = offer["titre"]
    if offer["entreprise"] and has_any(offer["entreprise"], cfg["esn_blacklist"]):
        return False, "ESN / cabinet"
    if has_any(titre, cfg["mots_exclus"]):
        return False, "mot exclu dans le titre"
    if not has_any(titre, cfg["mots_requis"]):
        return False, "intitulé hors cible"
    lieu = offer["lieu"].lower()
    if lieu and not any(v in lieu for v in cfg["villes_ok"]):
        return False, f"lieu hors zone ({offer['lieu']})"
    age = age_days(offer["date"])
    if age is not None and age > cfg["max_age_days"]:
        return False, f"trop ancienne ({age} j)"
    exp = experience_required(offer)
    if exp is not None and exp > cfg["max_experience_ans"]:
        return False, f"{exp} ans demandés"
    return True, ""
