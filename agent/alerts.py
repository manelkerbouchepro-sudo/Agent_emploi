"""Lit tes alertes e-mail (Indeed, Welcome to the Jungle, LinkedIn, APEC...) dans Gmail via IMAP.
Il faut un mot de passe d'application Google (compte avec validation en 2 étapes)."""
import email
import imaplib
import os
from datetime import date, timedelta
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime

from .util import extract_links, html_to_text, make_offer

IGNORE = ("unsubscribe", "desabonn", "désabonn", "preferences", "settings", "mailto:")


def parse_message(msg):
    subject = str(make_header(decode_header(msg.get("Subject", ""))))
    titre, ent = (subject.rsplit(" – ", 1) + [""])[:2] if " – " in subject else (subject, "")
    html_part = text_part = ""
    for part in msg.walk():
        ctype = part.get_content_type()
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        s = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/html":
            html_part = s
        elif ctype == "text/plain":
            text_part = s
    body = html_to_text(html_part) if html_part else text_part
    links = [u for u, _ in extract_links(html_part) if u.startswith("http") and not any(i in u.lower() for i in IGNORE)]
    try:
        d = parsedate_to_datetime(msg.get("Date")).isoformat()
    except Exception:
        d = ""
    return make_offer(id=msg.get("Message-ID", subject), titre=titre.strip(), entreprise=ent.strip(),
                      description=body[:3000], url=links[0] if links else "", date=d, source="alerte e-mail")


def fetch_alerts(cfg):
    user, pwd = os.environ.get("GMAIL_ADDRESS"), os.environ.get("GMAIL_APP_PASSWORD")
    if not (user and pwd):
        print("  alertes : GMAIL_ADDRESS / GMAIL_APP_PASSWORD absents, source ignorée")
        return []
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(user, pwd)
    M.select("INBOX", readonly=True)
    since = (date.today() - timedelta(days=cfg["max_age_days"])).strftime("%d-%b-%Y")
    ids = set()
    for sender in cfg["expediteurs_alertes"]:
        _, data = M.search(None, f'(SINCE {since} FROM "{sender}")')
        ids.update(data[0].split())
    offers = []
    for i in ids:
        _, d = M.fetch(i, "(RFC822)")
        offers.append(parse_message(email.message_from_bytes(d[0][1])))
    M.logout()
    print(f"  alertes : {len(offers)} mails")
    return offers
