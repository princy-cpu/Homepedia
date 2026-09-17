"""NLP des avis : sentiment + mots surveillés, puis synthèse par commune.

    docker compose run --rm tools python -m homepedia.nlp.sentiment --batch-size 32

Le modèle est configurable via SENTIMENT_MODEL (.env). Les libellés renvoyés
dépendent du modèle : adapter LABEL_TO_POLARITE après un premier essai.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import execute_values
from pymongo import MongoClient, UpdateOne

from homepedia.config import env, mongo_uri, scoring

# Correspondance libellé du modèle -> polarité dans [-1, 1]
# (ex. distilcamembert-base-sentiment renvoie "1 star" à "5 stars")
LABEL_TO_POLARITE = {
    "1 star": -1.0, "2 stars": -0.5, "3 stars": 0.0, "4 stars": 0.5, "5 stars": 1.0,
    "negative": -1.0, "neutral": 0.0, "positive": 1.0,
}


def polarite_to_label(p: float) -> str:
    return "negatif" if p < -0.2 else "positif" if p > 0.2 else "neutre"


def count_mentions(texte: str, mots: list[str]) -> dict[str, int]:
    t = texte.lower()
    return {m: n for m in mots if (n := len(re.findall(rf"\b{re.escape(m.lower())}\w*", t)))}


def analyse(batch_size: int, limit: int | None) -> None:
    from transformers import pipeline  # import tardif : lourd

    clf = pipeline("text-classification", model=env("SENTIMENT_MODEL"), truncation=True, max_length=512)
    mots = scoring()["nlp"]["mots_surveilles"]

    coll = MongoClient(mongo_uri())["homepedia"]["avis"]
    cursor = coll.find({"nlp": {"$exists": False}}, {"texte": 1})
    if limit:
        cursor = cursor.limit(limit)

    batch, done = [], 0
    for doc in cursor:
        batch.append(doc)
        if len(batch) == batch_size:
            done += _process(coll, clf, batch, mots)
            batch = []
    if batch:
        done += _process(coll, clf, batch, mots)
    print(f"[nlp] {done} avis analysés")


def _process(coll, clf, batch, mots) -> int:
    preds = clf([d["texte"] for d in batch])
    ops = []
    for doc, pred in zip(batch, preds):
        pol = LABEL_TO_POLARITE.get(pred["label"].lower(), 0.0)
        ops.append(
            UpdateOne(
                {"_id": doc["_id"]},
                {"$set": {"nlp": {
                    "sentiment": polarite_to_label(pol),
                    "polarite": pol,
                    "label_modele": pred["label"],
                    "confiance": round(float(pred["score"]), 4),
                    "mentions": count_mentions(doc["texte"], mots),
                    "themes": [],  # TODO : zero-shot / BERTopic (voir docs/05_ia.md)
                    "analyse_le": datetime.now(timezone.utc),
                }}},
            )
        )
    coll.bulk_write(ops, ordered=False)
    return len(ops)


def synthese() -> None:
    """Agrège par commune dans MongoDB puis reporte dans PostgreSQL."""
    db = MongoClient(mongo_uri())["homepedia"]
    pipeline = [
        {"$match": {"nlp": {"$exists": True}}},
        {"$group": {
            "_id": "$code_insee",
            "nb_avis": {"$sum": 1},
            "sentiment_moyen": {"$avg": "$nlp.polarite"},
            "positif": {"$sum": {"$cond": [{"$eq": ["$nlp.sentiment", "positif"]}, 1, 0]}},
            "neutre": {"$sum": {"$cond": [{"$eq": ["$nlp.sentiment", "neutre"]}, 1, 0]}},
            "negatif": {"$sum": {"$cond": [{"$eq": ["$nlp.sentiment", "negatif"]}, 1, 0]}},
            "mentions": {"$push": "$nlp.mentions"},
        }},
    ]
    rows = []
    for r in db["avis"].aggregate(pipeline, allowDiskUse=True):
        mentions = Counter()
        for m in r["mentions"]:
            mentions.update(m or {})
        doc = {
            "code_insee": r["_id"],
            "nb_avis": r["nb_avis"],
            "sentiment_moyen": round(r["sentiment_moyen"], 3),
            "repartition": {k: r[k] for k in ("positif", "neutre", "negatif")},
            "mentions": dict(mentions),
            "top_themes": [],
            "maj_le": datetime.now(timezone.utc),
        }
        db["nlp_synthese_commune"].replace_one({"code_insee": doc["code_insee"]}, doc, upsert=True)
        rows.append((doc["code_insee"], doc["nb_avis"], doc["sentiment_moyen"], doc["top_themes"]))

    if rows:
        with psycopg2.connect(
            host=env("POSTGRES_HOST", "localhost"), dbname=env("POSTGRES_DB"),
            user=env("POSTGRES_USER"), password=env("POSTGRES_PASSWORD"),
        ) as conn, conn.cursor() as cur:
            execute_values(
                cur,
                """INSERT INTO fact_avis_synthese (code_insee, nb_avis, sentiment_moyen, top_themes)
                   VALUES %s
                   ON CONFLICT (code_insee) DO UPDATE SET
                     nb_avis = EXCLUDED.nb_avis, sentiment_moyen = EXCLUDED.sentiment_moyen,
                     top_themes = EXCLUDED.top_themes, maj_le = now()""",
                rows,
            )
    print(f"[nlp] synthèse : {len(rows)} communes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--synthese-seule", action="store_true")
    args = parser.parse_args()
    if not args.synthese_seule:
        analyse(args.batch_size, args.limit)
    synthese()


if __name__ == "__main__":
    main()
