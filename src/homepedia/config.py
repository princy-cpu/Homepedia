"""Configuration centralisée : variables d'environnement et fichiers YAML."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

PROJECT_ROOT = Path(os.getenv("HOMEPEDIA_ROOT", Path(__file__).resolve().parents[2]))
CONFIG_DIR = PROJECT_ROOT / "config"


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Variable d'environnement manquante : {name}")
    return value


@lru_cache
def sources() -> dict:
    with open(CONFIG_DIR / "sources.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]


@lru_cache
def scoring() -> dict:
    with open(CONFIG_DIR / "scoring.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def dev_departements() -> list[str]:
    """Départements à traiter en développement (vide = tous)."""
    raw = os.getenv("DEV_DEPARTEMENTS", "").strip()
    return [d.strip().zfill(2) for d in raw.split(",") if d.strip()]


def postgres_url(driver: str = "postgresql+psycopg2") -> str:
    return (
        f"{driver}://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}"
        f"@{env('POSTGRES_HOST', 'localhost')}:{env('POSTGRES_PORT', '5432')}/{env('POSTGRES_DB')}"
    )


def postgres_jdbc() -> tuple[str, dict]:
    url = (
        f"jdbc:postgresql://{env('POSTGRES_HOST', 'localhost')}:"
        f"{env('POSTGRES_PORT', '5432')}/{env('POSTGRES_DB')}"
    )
    props = {
        "user": env("POSTGRES_USER"),
        "password": env("POSTGRES_PASSWORD"),
        "driver": "org.postgresql.Driver",
    }
    return url, props


def mongo_uri() -> str:
    return env("MONGO_URI", "mongodb://localhost:27017")
