"""Agent de recherche d'emploi : cherche -> filtre -> vérifie -> note -> rapport.
Usage :
  python main.py --demo --no-llm   # test sans réseau ni clé
  python main.py                   # recherche réelle (les sources sans clé sont passées)
  python main.py --tout            # remontre aussi les offres déjà vues
"""
import argparse
import json
import os
import sys
import webbrowser

from dotenv import load_dotenv

from agent import alerts, careers, filters, report, scorer, seen, sources, targets, verifier, websearch

# Clés nécessaires par source : une source sans ses clés est passée, sans faire planter l'agent.
NEEDS = {
    "alertes": ["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"],
    "carrieres": [],
    "web": ["ANTHROPIC_API_KEY"],
    "france_travail": ["FT_CLIENT_ID", "FT_CLIENT_SECRET"],
}
FETCH = {
    "alertes": alerts.fetch_alerts,
    "carrieres": careers.fetch_all,
    "web": websearch.fetch_all,
    "france_travail": sources.fetch_all,
}


def gather(cfg, chosen):
    names = chosen.split(",") if chosen else cfg["sources"]
    offers = []
    for n in names:
        n = n.strip()
        if n not in FETCH:
            print(f"Source inconnue : {n} (choix : {', '.join(FETCH)})")
            continue
        missing = [k for k in NEEDS[n] if not os.environ.get(k)]
        if missing:
            print(f"Source {n} : passée, il manque {', '.join(missing)} dans .env")
            continue
        print(f"Source : {n}")
        try:
            res = FETCH[n](cfg)
            for o in res:
                o.setdefault("source", n)
            offers += res
        except Exception as e:  # une source en panne ne doit pas bloquer les autres
            print(f"  ! source {n} en échec : {e}")
    return offers


def dedupe(offers):
    seen_keys, out = set(), []
    for o in offers:
        key = (o["titre"].lower().strip(), o["entreprise"].lower().strip())
        if (o["url"] and o["url"] in seen_keys) or key in seen_keys:
            continue
        seen_keys.update({o["url"], key} if o["url"] else {key})
        out.append(o)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="utilise demo_offers.json")
    ap.add_argument("--sources", help="ex: alertes,carrieres,web,france_travail (défaut : config.json)")
    ap.add_argument("--no-llm", action="store_true", help="note par mots-clés, sans API Claude")
    ap.add_argument("--tout", action="store_true", help="inclut les offres déjà vues lors des lancements précédents")
    ap.add_argument("--pas-de-navigateur", action="store_true", help="n'ouvre pas le rapport à la fin")
    args = ap.parse_args()
    load_dotenv()
    if hasattr(sys.stdout, "reconfigure"):  # accents corrects dans la console Windows
        sys.stdout.reconfigure(encoding="utf-8")

    cfg = json.load(open("config.json", encoding="utf-8"))
    profil = json.load(open("profil.json", encoding="utf-8"))
    cfg["cibles"] = targets.load()
    idx = targets.index(cfg["cibles"])
    if cfg["cibles"]:
        print(f"Liste d'entreprises cibles : {len(cfg['cibles'])} (cibles.json)")

    use_llm = not args.no_llm and bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not args.no_llm and not use_llm:
        print("ANTHROPIC_API_KEY absente : notation par mots-clés (moins fine).")

    offers = json.load(open("demo_offers.json", encoding="utf-8")) if args.demo else gather(cfg, args.sources)
    offers = dedupe(offers)
    print(f"{len(offers)} offres récupérées")

    memory = {} if args.demo else seen.load()
    if not args.tout:
        offers, old = seen.split_new(offers, memory)
        if old:
            print(f"{len(old)} déjà vues lors d'un lancement précédent (--tout pour les revoir)")

    kept, rejected = [], []
    for o in offers:
        ok, why = filters.keep(o, cfg)
        (kept if ok else rejected).append(o if ok else (o, why))
    print(f"{len(kept)} gardées, {len(rejected)} écartées par les filtres")

    limit = cfg.get("max_offres_notees", 40)
    if use_llm and len(kept) > limit:
        print(f"Plus de {limit} offres : seules les {limit} plus récentes sont notées par Claude (max_offres_notees).")
        kept.sort(key=lambda o: o["date"] or "", reverse=True)
        skipped = {id(o) for o in kept[limit:]}  # non notées : on les garde pour le prochain lancement
        offers = [o for o in offers if id(o) not in skipped]
        kept = kept[:limit]

    results = []
    for i, o in enumerate(kept, 1):
        o["alive"] = None if args.demo else verifier.is_alive(o["url"])
        if o["alive"] is False:
            rejected.append((o, "lien mort"))
            continue
        try:
            o["eval"] = scorer.score_with_claude(o, profil) if use_llm else scorer.score_keywords(o, profil)
        except Exception as e:  # l'agent ne doit jamais s'arrêter sur une offre
            print(f"  ! notation impossible pour {o['titre']} : {e}")
            o["eval"] = scorer.score_keywords(o, profil)
        o["cible"] = targets.match(o["entreprise"], idx)
        tag = f"  [liste {o['cible']}]" if o["cible"] else ""
        print(f"  [{i}/{len(kept)}] {o['eval']['score']}/10  {o['titre']} — {o['entreprise']}{tag}")
        minimum = cfg.get("score_minimum_cibles", cfg["score_minimum"]) if o["cible"] else cfg["score_minimum"]
        if o["eval"]["score"] >= minimum:
            results.append(o)
        else:
            rejected.append((o, f"score {o['eval']['score']}/10"))

    # tri : note d'abord, puis entreprises de ta liste (A avant B avant C) à note égale
    results.sort(key=lambda x: (-x["eval"]["score"], x.get("cible") or "Z"))
    def pl(n, sing, plur):
        return f"{n} {sing if n <= 1 else plur}"
    stats = (f"{pl(len(results), 'offre retenue', 'offres retenues')} · "
             f"{pl(len(kept), 'examinée', 'examinées')} · "
             f"dont {sum(1 for o in results if o.get('cible'))} de ta liste · "
             f"notation {'Claude' if use_llm else 'par mots-clés'}")
    path = report.write_report(results, rejected, stats)
    if not args.demo:
        seen.remember(offers, memory)
    print("Rapport :", os.path.abspath(path))
    if not args.pas_de_navigateur:
        webbrowser.open("file://" + os.path.abspath(path))


if __name__ == "__main__":
    main()
