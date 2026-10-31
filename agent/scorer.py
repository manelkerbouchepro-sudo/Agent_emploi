"""Note chaque offre /10 par rapport à profil.json avec l'API Claude."""
import json
import os

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

SYSTEM = """Tu évalues la correspondance entre une offre d'emploi et un profil de candidate junior.
Règles strictes :
- N'invente JAMAIS une compétence. Une compétence listée en 'autoformation' n'est pas maîtrisée.
- Sois sévère et honnête : une exigence éliminatoire (années d'expérience, technologie absente) fait chuter la note.
- Réponds UNIQUEMENT par un objet JSON :
{"score": entier 0-10, "verdict": "postuler" | "peut-être" | "ignorer",
 "points_forts": [...], "manques": [...], "raison": "une phrase"}"""


def _parse(text):
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def score_with_claude(offer, profil):
    from anthropic import Anthropic
    client = Anthropic()
    payload = {
        "profil": profil,
        "offre": {
            "titre": offer["titre"], "entreprise": offer["entreprise"],
            "lieu": offer["lieu"], "experience": offer["experience"],
            "description": offer["description"][:4000],
        },
    }
    msg = client.messages.create(
        model=MODEL, max_tokens=600, system=SYSTEM,
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    return _parse(msg.content[0].text)


def score_keywords(offer, profil):
    """Mode test sans API : compte les compétences maîtrisées citées dans l'offre."""
    text = f"{offer['titre']} {offer['description']}".lower()
    import re
    def cite(kw):
        return re.search(r"(?<![a-z0-9])" + re.escape(kw.lower()) + r"(?![a-z0-9+#])", text)
    hits = [s for s in profil["maitrise"] if cite(s.split(" (")[0])]
    score = min(10, 2 + len(hits))
    return {"score": score, "verdict": "peut-être" if score >= 5 else "ignorer",
            "points_forts": hits, "manques": [], "raison": "score par mots-clés (mode sans IA)"}
