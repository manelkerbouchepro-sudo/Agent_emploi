import html
import re
from urllib.parse import urljoin


def html_to_text(h):
    h = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", h or "")
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def extract_links(h, base=""):
    pat = r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
    return [(urljoin(base, m.group(1)), html_to_text(m.group(2))) for m in re.finditer(pat, h or "")]


def make_offer(**kw):
    o = {"id": "", "titre": "", "entreprise": "", "lieu": "", "contrat": "",
         "experience": "", "date": "", "description": "", "url": "", "source": ""}
    o.update(kw)
    return o
