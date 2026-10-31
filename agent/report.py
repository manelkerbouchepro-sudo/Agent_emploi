"""Écrit le rapport du jour en Markdown (pour GitHub) et en HTML (à ouvrir dans le navigateur)."""
import html
import os
from datetime import date

VIVANT = {True: "en ligne", False: "lien mort", None: "à vérifier"}


def _md(results, rejected, stats):
    lines = [f"# Offres du {date.today()}", "", stats, ""]
    for o in results:
        s = o["eval"]
        lines += [
            f"## {s['score']}/10 · {o['titre']} — {o['entreprise'] or 'entreprise non indiquée'}"
            + (f" · liste {o['cible']}" if o.get("cible") else ""),
            f"- Lieu : {o['lieu'] or '—'} · Contrat : {o['contrat'] or '—'} · Expérience : {o['experience'] or 'non indiquée'}",
            f"- Publiée : {o['date'][:10] or '—'} · Source : {o.get('source') or '—'} · Lien : {VIVANT[o.get('alive')]}",
            f"- Verdict : **{s['verdict']}** — {s['raison']}",
            f"- Points forts : {', '.join(s['points_forts']) or '—'}",
            f"- Manques : {', '.join(s['manques']) or '—'}",
            f"- {o['url']}", "",
        ]
    lines += ["---", f"{len(rejected)} offres écartées :"]
    lines += [f"- {o['titre']} ({o['entreprise'] or '—'}) : {why}" for o, why in rejected[:60]]
    return "\n".join(lines)


CSS = """
:root{--bg:#f7f8fb;--card:#fff;--ink:#1b2333;--muted:#5f6b7d;--line:#e3e7ee;--navy:#1f3a6e;
--good:#1d7a4c;--mid:#a46a00;--low:#9a3b3b}
@media (prefers-color-scheme:dark){:root{--bg:#12161d;--card:#1b212b;--ink:#e6e9ef;--muted:#9aa5b5;
--line:#2c3441;--navy:#8fb0ea;--good:#5cc893;--mid:#e0a94a;--low:#e08a8a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:22px;margin:0 0 4px;color:var(--navy)}.stats{color:var(--muted);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:0 0 12px}
.top{display:flex;gap:12px;align-items:flex-start}
.score{flex:none;min-width:48px;text-align:center;font-weight:700;font-size:18px;border-radius:8px;padding:6px 0;
border:2px solid currentColor}.s-good{color:var(--good)}.s-mid{color:var(--mid)}.s-low{color:var(--low)}
.badge{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:99px;margin-left:6px;
vertical-align:2px;background:var(--navy);color:var(--card)}
.title{font-weight:650;font-size:16px}.title a{color:inherit}.meta{color:var(--muted);font-size:13px}
.why{margin:8px 0 4px}.tags{font-size:13px}.tags b{font-weight:600}
details{margin-top:24px;color:var(--muted)}summary{cursor:pointer}
details li{margin:2px 0}
"""


def _html(results, rejected, stats):
    e = html.escape
    cards = []
    for o in results:
        s = o["eval"]
        cls = "s-good" if s["score"] >= 7 else "s-mid" if s["score"] >= 5 else "s-low"
        title = e(o["titre"])
        if o["url"]:
            title = f'<a href="{e(o["url"])}" target="_blank" rel="noopener">{title}</a>'
        if o.get("cible"):
            title += f' <span class="badge">ta liste · {e(o["cible"])}</span>'
        meta = " · ".join(x for x in [
            e(o["entreprise"] or "entreprise non indiquée"), e(o["lieu"]), e(o["contrat"]),
            e(o["experience"] or ""), ("publiée " + e(o["date"][:10])) if o["date"] else "",
            e(o.get("source") or ""), VIVANT[o.get("alive")]] if x)
        cards.append(f"""<div class="card"><div class="top"><div class="score {cls}">{s['score']}</div><div>
<div class="title">{title}</div><div class="meta">{meta}</div>
<div class="why"><b>{e(s['verdict'])}</b> — {e(s['raison'])}</div>
<div class="tags"><b>Points forts :</b> {e(', '.join(s['points_forts']) or '—')}<br>
<b>Manques :</b> {e(', '.join(s['manques']) or '—')}</div></div></div></div>""")
    if not cards:
        cards.append('<div class="card">Aucune nouvelle offre au-dessus du score minimum aujourd\'hui.</div>')
    rej = "".join(f"<li>{e(o['titre'])} ({e(o['entreprise'] or '—')}) : {e(why)}</li>" for o, why in rejected[:120])
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Offres du {date.today()}</title>
<style>{CSS}</style></head><body><main><h1>Offres du {date.today()}</h1><p class="stats">{e(stats)}</p>
{''.join(cards)}<details><summary>{len(rejected)} offres écartées</summary><ul>{rej}</ul></details>
</main></body></html>"""


def write_report(results, rejected, stats="", outdir="output"):
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, f"rapport_{date.today()}")
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(_md(results, rejected, stats))
    with open(base + ".html", "w", encoding="utf-8") as f:
        f.write(_html(results, rejected, stats))
    return base + ".html"
