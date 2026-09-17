"""Ingestion des sources "http" déclarées dans config/sources.yaml vers le bronze (MinIO).

Usage :
    python -m homepedia.ingestion.download --list
    python -m homepedia.ingestion.download dvf api_geo
    python -m homepedia.ingestion.download --all
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from homepedia.config import sources
from homepedia.lake import ensure_buckets, upload_raw

TIMEOUT = 120
CHUNK = 1 << 20  # 1 Mo


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def fetch(url: str, dest: Path) -> Path:
    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(CHUNK):
                f.write(chunk)
    return dest


def file_name_for(url: str, source: str, index: int) -> str:
    """Nom de fichier lisible et unique (les URL data.gouv finissent souvent pareil)."""
    parsed = urlparse(url)
    name = Path(parsed.path).name or f"{source}_{index}"
    if parsed.query:  # API renvoyant du JSON
        name = f"{source}_{index}.json"
    return name


def urls_for(cfg: dict) -> list[str]:
    if "url_template" in cfg:
        return [cfg["url_template"].format(year=y) for y in cfg.get("years", [])]
    return list(cfg.get("urls") or [])


def ingest(source_id: str) -> list[str]:
    cfg = sources()[source_id]
    if cfg.get("type") != "http":
        print(f"[skip] {source_id} : type '{cfg.get('type')}' géré par un autre module")
        return []
    urls = urls_for(cfg)
    if not urls:
        print(f"[todo] {source_id} : aucune URL renseignée dans sources.yaml ({cfg['page']})")
        return []

    written = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, url in enumerate(urls):
            name = file_name_for(url, source_id, i)
            # DVF : un dossier par année pour éviter les collisions "full.csv.gz"
            if "url_template" in cfg:
                name = f"{source_id}_{cfg['years'][i]}_{name}"
            local = Path(tmp) / name
            print(f"[get] {source_id} <- {url}")
            fetch(url, local)
            key = upload_raw(local, source_id, url)
            print(f"[ok]  {key} ({local.stat().st_size / 1e6:.1f} Mo)")
            written.append(key)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="*", help="identifiants de sources (voir --list)")
    parser.add_argument("--all", action="store_true", help="toutes les sources http")
    parser.add_argument("--list", action="store_true", help="lister les sources")
    args = parser.parse_args()

    if args.list:
        for sid, cfg in sources().items():
            n = len(urls_for(cfg))
            print(f"{sid:<22} {cfg['type']:<7} {n:>2} URL  {cfg['label']}")
        return

    ensure_buckets()
    targets = list(sources()) if args.all else args.sources
    if not targets:
        parser.error("indiquer au moins une source, ou --all")
    for sid in targets:
        ingest(sid)


if __name__ == "__main__":
    main()
