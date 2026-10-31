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

# 7. liste d'entreprises cibles
from agent import targets
rows = [
    ("Génie logiciel", "Datadog", None, "Paris / Île-de-France", "Paris", "Monitoring cloud", "datadoghq.com"),
    ("Mécatronique", "Forvia (ex-Faurecia)", None, "Paris / Île-de-France", "Nanterre", "Sièges & intérieurs mécatroniques", "forvia.com"),
    ("Génie logiciel", "Algolia", "PME / Startup", "Paris / Île-de-France", "Paris", "Moteur de recherche SaaS", "algolia.com"),
    ("Électronique & systèmes embarqués", "Stellantis", None, "Nancy / Metz", "Trémery", "Moteurs électriques", "stellantis.com"),
    ("Robotique", "Stellantis", None, "Nancy / Metz", "Trémery", "Moteurs électriques", "stellantis.com"),
    ("Génie logiciel", "Capgemini", None, "Nancy / Metz", "Nancy", "ESN", "capgemini.com"),
    ("Robotique", "Thales", "Militaire / Défense / Spatial", "Paris / Île-de-France", "Paris", "Radars", "thalesgroup.com"),
    ("Génie logiciel", "Inria (centre de recherche)", None, "Nancy / Metz", "Villers", "Recherche IA", "inria.fr"),
    ("Biologie / Biotech / Santé", "Sanofi", None, "Paris / Île-de-France", "Paris", "Pharma", "sanofi.com"),
    ("Génie logiciel", "Doctolib", "PME / Startup", "Lyon", "Lyon", "HealthTech", "doctolib.fr"),
]
c = targets.from_rows(rows, cfg)
p = {x["nom"]: x["priorite"] for x in c}
assert p == {"Stellantis": "A", "Forvia (ex-Faurecia)": "A", "Datadog": "B", "Algolia": "B",
             "Thales": "C", "Inria (centre de recherche)": "B"}, p
assert [x["nom"] for x in c][0] == "Stellantis"          # Grand Est en tête
assert next(x for x in c if x["nom"] == "Stellantis")["domaines"] == ["Électronique", "Robotique"]
idx = targets.index(c)
assert targets.match("Valeo", idx) is None
assert targets.match("Forvia", idx) == "A" and targets.match("FORVIA Group", idx) == "A"
assert targets.match("Stellantis Automobiles SAS", idx) == "A"
assert targets.match("Capgemini", idx) is None and targets.match("", idx) is None
q = targets.web_queries(c, max_queries=2)
assert len(q) == 2 and '"Stellantis"' in q[0] and "Nancy" in q[0] and "(" not in q[1], q

# 8. lecture Workable (réponse simulée)
import unittest.mock as um
fake = um.Mock(); fake.json.return_value = {"jobs": [{"title": "ML Engineer", "shortcode": "AB12", "city": "Paris",
    "country": "France", "employment_type": "Full-time", "published_on": "2026-10-20", "url": "https://apply.workable.com/j/AB12"}]}
with um.patch.object(careers, "_get", return_value=fake):
    w = careers.workable({"nom": "Hugging Face", "slug": "huggingface"})
assert w[0]["lieu"] == "Paris, France" and w[0]["url"].endswith("AB12") and w[0]["entreprise"] == "Hugging Face"
assert filters.keep({**w[0], "experience": "", "description": ""}, cfg)[0]

# 9. badge « ta liste » dans le rapport
o2["cible"] = "A"
h = open(report.write_report([o2], [], "s", outdir=tempfile.mkdtemp()), encoding="utf-8").read()
assert "ta liste · A" in h
print("OK : tous les tests passent")
