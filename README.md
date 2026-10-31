# Agent de recherche d'emploi

Rassemble des offres CDI depuis plusieurs sources légales, écarte les ESN, les offres trop
anciennes, hors zone ou trop exigeantes, vérifie que le lien existe encore, puis note chaque offre
sur 10 par rapport à `profil.json` avec l'API Claude. Chaque lancement ne montre que les **nouvelles**
offres, dans un rapport HTML qui s'ouvre tout seul dans le navigateur (copie Markdown dans `output/`).

## Démarrage rapide (Windows)
1. Installe Python 3.10 ou plus récent (python.org, coche « Add Python to PATH »).
2. Double-clique sur **`lancer.bat`**. La première fois, il crée `.env` et l'ouvre dans le Bloc-notes :
   colle ta clé `ANTHROPIC_API_KEY` (console.anthropic.com), enregistre, ferme.
3. Double-clique de nouveau sur `lancer.bat` : il installe les dépendances (une seule fois), cherche, note
   et ouvre le rapport.

Sans clé Anthropic, l'agent fonctionne quand même : il note par mots-clés et passe la recherche web.

## Sources (config.json > "sources")
| Source | Ce que ça lit | Clé nécessaire |
|---|---|---|
| `carrieres` | Pages carrières des entreprises de `companies.json` (Lever, Greenhouse, SmartRecruiters, ou page HTML) | aucune |
| `web` | Recherche web via l'outil intégré à l'API Claude | `ANTHROPIC_API_KEY` |
| `alertes` | Tes mails d'alerte (Indeed, Welcome to the Jungle, LinkedIn, APEC) dans Gmail | `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` |
| `france_travail` | API Offres d'emploi v2 | `FT_CLIENT_ID` + `FT_CLIENT_SECRET` |

Une source dont la clé manque est simplement passée, avec un message. Une source en panne n'arrête pas les autres.
L'agent ne lit pas Indeed, LinkedIn ni Welcome to the Jungle directement (interdit par leurs conditions) :
crée des alertes e-mail sur ces sites, l'agent lit les mails.

## Commandes utiles
- `lancer.bat` ou `python main.py` : recherche du jour, nouvelles offres seulement
- `python main.py --tout` : remontre aussi les offres déjà vues
- `python main.py --sources carrieres,web` : seulement certaines sources
- `python main.py --no-llm` : notation par mots-clés, sans appel à Claude
- `python tests/test_offline.py` puis `python main.py --demo --no-llm` : tests sans réseau

## Réglages (config.json)
- `villes_ok`, `max_experience_ans`, `max_age_days` : zone, niveau et fraîcheur des offres
- `mots_requis` / `mots_exclus` : mots entiers cherchés dans l'intitulé (« ia » ne capte plus « commercial »)
- `esn_blacklist` : sociétés écartées
- `score_minimum` : note en dessous de laquelle une offre n'apparaît pas dans le rapport
- `max_offres_notees` : nombre maximum d'offres notées par Claude par lancement (maîtrise du coût) ;
  les offres non notées restent pour le lancement suivant

## Ajouter une entreprise (companies.json)
- Adresse des offres en `jobs.lever.co/NOM` : `{"nom":"X","type":"lever","slug":"NOM"}`
- `boards.greenhouse.io/NOM` : type `greenhouse` ; `jobs.smartrecruiters.com/NOM` : type `smartrecruiters`
- Sinon : `{"nom":"X","type":"page","url":"https://...liste des offres..."}`. Les pages qui chargent leurs
  offres en JavaScript peuvent revenir vides ; les URL marquées `a_verifier` sont à contrôler.

## Mot de passe d'application Gmail
Compte Google > Sécurité > Validation en 2 étapes > Mots de passe des applications.

## Principes
- `profil.json` est la seule source de vérité : l'agent n'invente aucune compétence.
- L'agent ne postule jamais seul : tu relis le rapport et tu décides.
- Lance-le une fois par jour, sans boucle. Ne publie jamais `.env` ni `deja_vues.json`.
