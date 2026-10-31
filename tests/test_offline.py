"""Tests sans réseau : python tests/test_offline.py"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from email.message import EmailMessage
from agent import alerts, careers, filters
cfg = json.load(open("config.json", encoding="utf-8"))

# 1. page carrière générique
html = '<a href="/offre/12">Développeur C# .NET (H/F)</a><a href="/about">À propos</a><a href="/offre/13">Ingénieur logiciel embarqué</a>'
links = careers.parse_page_html(html, "https://exemple.fr/jobs", cfg["mots_requis"])
assert [t for _, t in links] == ["Développeur C# .NET (H/F)", "Ingénieur logiciel embarqué"], links
assert links[0][0] == "https://exemple.fr/offre/12"

# 2. mail d'alerte
m = EmailMessage(); m["Subject"] = "Développeur Junior - C#/SQL (F/H) – Natixis"; m["Date"] = "Sun, 11 Oct 2026 05:26:42 +0000"
m.set_content("Votre parcours pourrait correspondre."); m.add_alternative('<a href="https://fr.indeed.com/viewjob?jk=1">Voir</a><a href="https://x/unsubscribe">stop</a>', subtype="html")
o = alerts.parse_message(m)
assert o["titre"] == "Développeur Junior - C#/SQL (F/H)" and o["entreprise"] == "Natixis" and "viewjob" in o["url"], o

# 3. filtres
base = {"titre": "Développeur .NET", "entreprise": "Éditeur", "lieu": "54 - NANCY", "experience": "", "description": "", "date": ""}
assert filters.keep(base, cfg)[0]
assert not filters.keep({**base, "lieu": "Lyon"}, cfg)[0]
assert not filters.keep({**base, "entreprise": "Atos"}, cfg)[0]
assert not filters.keep({**base, "titre": "Responsable de magasin"}, cfg)[0]
assert not filters.keep({**base, "description": "3 ans d'expérience minimum"}, cfg)[0]

# 4. mots entiers : « ia » / « ai » ne doivent plus laisser passer n'importe quoi
for t in ["Commercial sédentaire", "Technicien de maintenance", "Chargé d'affaires", "Assistante administrative"]:
    assert not filters.keep({**base, "titre": t}, cfg)[0], t
for t in ["Ingénieure IA", "Développeuse C#", "Data Engineer junior", "Ingénieur(e) logiciel embarqué", "AI Engineer"]:
    assert filters.keep({**base, "titre": t}, cfg)[0], t
assert not filters.keep({**base, "titre": "Tech Leader .NET"}, cfg)[0]
assert not filters.keep({**base, "entreprise": "SII Est"}, cfg)[0]
assert filters.keep({**base, "entreprise": "Siemens"}, cfg)[0]  # « sii » ne doit pas toucher Siemens
links = careers.parse_page_html('<a href="/m">Mentions légales et maintenance</a>', "https://x.fr", cfg["mots_requis"])
assert links == [], links

# 5. offres déjà vues
import tempfile
from agent import seen, report
p = os.path.join(tempfile.mkdtemp(), "vues.json")
o1 = {**base, "url": "https://x/1"}; o2 = {**base, "titre": "Développeur C#", "url": "https://x/2"}
mem = seen.load(p); assert mem == {}
seen.remember([o1], mem, p)
new, old = seen.split_new([o1, o2], seen.load(p))
assert new == [o2] and old == [o1]

# 6. rapport HTML : lien cliquable et texte échappé
o2.update(eval={"score": 8, "verdict": "postuler", "raison": "C# <et> .NET", "points_forts": ["C#"], "manques": []},
          alive=True, contrat="CDI", source="carrière")
d = tempfile.mkdtemp()
path = report.write_report([o2], [(o1, "test")], "stats", outdir=d)
h = open(path, encoding="utf-8").read()
assert 'href="https://x/2"' in h and "C# &lt;et&gt; .NET" in h and os.path.exists(path[:-5] + ".md")
print("OK : tous les tests passent")
