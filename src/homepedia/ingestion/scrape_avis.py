"""Collecte des avis d'habitants (source textuelle) vers MongoDB.

Principes (à rappeler en soutenance) :
  * respect du robots.txt et délai entre requêtes (SCRAPER_DELAY_SECONDS) ;
  * User-Agent identifié ; cache MongoDB pour ne jamais re-télécharger une page ;
  * aucune donnée personnelle conservée (pseudonymes ignorés).

Usage :
    python -m homepedia.ingestion.scrape_avis --communes 69123 75056 --max-pages 3

⚠️ Les sélecteurs CSS ci-dessous sont des EXEMPLES à adapter après inspection
du HTML réel du site (clic droit > Inspecter).
"""
from __future__ import annotations

import argparse
import hashlib
import time
import unicodedata
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient, UpdateOne

from homepedia.config import env, mongo_uri

BASE_URL = "https://www.ville-ideale.fr/"
USER_AGENT = env("SCRAPER_USER_AGENT", "HomepediaStudentBot/0.1")
DELAY = float(env("SCRAPER_DELAY_SECONDS", "2"))

# --- À ADAPTER après inspection du site -----------------------------------
SELECTOR_AVIS = "div.avis"            # bloc d'un avis
SELECTOR_TEXTE = "p.comm"             # texte de l'avis
SELECTOR_DATE = "p.date"              # date
SELECTOR_NOTES = "table.notes td"     # notes détaillées (optionnel)
# ---------------------------------------------------------------------------


def db():
    return MongoClient(mongo_uri())["homepedia"]


def robots_ok(url: str) -> bool:
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(BASE_URL, "/robots.txt"))
    try:
        rp.read()
    except Exception:  # robots.txt injoignable : on reste prudent
        return False
    return rp.can_fetch(USER_AGENT, url)


def get_page(session: requests.Session, url: str) -> str | None:
    cache = db()["scrape_cache"]
    hit = cache.find_one({"url": url})
    if hit:
        return hit["html"]
    if not robots_ok(url):
        print(f"[robots] interdit : {url}")
        return None
    time.sleep(DELAY)
    r = session.get(url, timeout=30)
    if r.status_code != 200:
        print(f"[{r.status_code}] {url}")
        return None
    cache.update_one(
        {"url": url},
        {"$set": {"html": r.text, "fetched_at": datetime.now(timezone.utc)}},
        upsert=True,
    )
    return r.text


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    return " ".join(text.replace("\xa0", " ").split())


def parse_avis(html: str, code_insee: str, url: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    docs = []
    for bloc in soup.select(SELECTOR_AVIS):
        texte_el = bloc.select_one(SELECTOR_TEXTE)
        if not texte_el:
            continue
        texte = clean_text(texte_el.get_text(" "))
        if len(texte) < 10:
            continue
        date_el = bloc.select_one(SELECTOR_DATE)
        docs.append(
            {
                "code_insee": code_insee,
                "source": "ville-ideale",
                "url": url,
                "date_avis": clean_text(date_el.get_text()) if date_el else None,
                "date_collecte": datetime.now(timezone.utc),
                "texte": texte,
                "texte_hash": hashlib.sha256(texte.encode("utf-8")).hexdigest(),
                "notes": {},  # TODO : parser SELECTOR_NOTES
            }
        )
    return docs


def url_commune(code_insee: str, page: int) -> str:
    # TODO : le site utilise un slug "nom-de-la-commune_code" ; le construire
    # depuis ref_commune (PostgreSQL) après inspection des URL réelles.
    return urljoin(BASE_URL, f"{code_insee}?page={page}")


def scrape(communes: list[str], max_pages: int) -> None:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    coll = db()["avis"]
    for code in communes:
        total = 0
        for page in range(1, max_pages + 1):
            url = url_commune(code, page)
            html = get_page(session, url)
            if not html:
                break
            docs = parse_avis(html, code, url)
            if not docs:
                break
            ops = [UpdateOne({"texte_hash": d["texte_hash"]}, {"$setOnInsert": d}, upsert=True) for d in docs]
            coll.bulk_write(ops, ordered=False)
            total += len(docs)
        print(f"[avis] {code} : {total} avis")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--communes", nargs="+", required=True, help="codes INSEE")
    parser.add_argument("--max-pages", type=int, default=3)
    args = parser.parse_args()
    scrape(args.communes, args.max_pages)


if __name__ == "__main__":
    main()
