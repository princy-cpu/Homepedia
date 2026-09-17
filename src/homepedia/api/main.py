"""API FastAPI (bonus) : expose les indicateurs et les avis.

    docker compose --profile api up -d   ->  http://localhost:8000/docs
"""
# 🔧 EXERCICE E6/E9 : les routes /scores utilisent encore la table score_opportunite ;
# à adapter à score_territoire (potentiel, risque 2040, quadrant).

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from homepedia.config import mongo_uri, postgres_url

app = FastAPI(title="Homepedia API", version="0.1.0")
engine = create_engine(postgres_url(), pool_pre_ping=True)
mongo = MongoClient(mongo_uri())["homepedia"]

NIVEAUX = {"commune", "departement", "region"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/scores/{niveau}")
def scores(niveau: str, profil: str = "reseau_agences", limit: int = Query(20, le=500)) -> list[dict]:
    if niveau not in NIVEAUX:
        raise HTTPException(400, f"niveau doit être dans {sorted(NIVEAUX)}")
    sql = text(
        """SELECT * FROM score_opportunite
           WHERE niveau = :niveau AND profil = :profil
           ORDER BY rang LIMIT :limit"""
    )
    with engine.connect() as conn:
        return [dict(r._mapping) for r in conn.execute(sql, {"niveau": niveau, "profil": profil, "limit": limit})]


@app.get("/indicateurs/{niveau}/{code}")
def indicateurs(niveau: str, code: str) -> list[dict]:
    sql = text(
        """SELECT annee, indicateur, valeur FROM indicateur_territoire
           WHERE niveau = :niveau AND code = :code ORDER BY indicateur, annee"""
    )
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(sql, {"niveau": niveau, "code": code})]
    if not rows:
        raise HTTPException(404, "territoire inconnu ou sans données")
    return rows


@app.get("/avis/{code_insee}")
def avis(code_insee: str, sentiment: str | None = None, limit: int = Query(20, le=200)) -> dict:
    filtre = {"code_insee": code_insee}
    if sentiment:
        filtre["nlp.sentiment"] = sentiment
    synthese = mongo["nlp_synthese_commune"].find_one({"code_insee": code_insee}, {"_id": 0})
    items = list(
        mongo["avis"].find(filtre, {"_id": 0, "texte": 1, "date_avis": 1, "nlp.sentiment": 1}).limit(limit)
    )
    return {"synthese": synthese, "avis": items}
