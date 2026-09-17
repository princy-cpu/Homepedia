"""Publication des tables gold (Iceberg) vers la couche de service PostgreSQL.

    docker compose exec spark-master spark-submit src/homepedia/jobs/publish_to_postgres.py

On écrit en mode "overwrite + truncate" : la table PostgreSQL (et ses index,
définis dans db/postgres/init/01_schema.sql) est conservée, seul son contenu change.
"""
# 🔧 EXERCICE E4/E6 : mettre à jour MAPPING avec les nouvelles tables gold
# (score_territoire, segment_bien, valeur_verte...).

from __future__ import annotations

import psycopg2

from homepedia.config import env, postgres_jdbc
from homepedia.jobs.common import get_spark

# table gold Iceberg  ->  table PostgreSQL
MAPPING = {
    "iceberg.gold.gold_marche_commune": "fact_marche",
    "iceberg.gold.gold_indicateur_territoire": "indicateur_territoire",
    "iceberg.gold.gold_score_opportunite": "score_opportunite",
}

MATERIALIZED_VIEWS = ["mv_marche_departement", "mv_marche_region"]


def refresh_views() -> None:
    conn = psycopg2.connect(
        host=env("POSTGRES_HOST", "localhost"),
        dbname=env("POSTGRES_DB"),
        user=env("POSTGRES_USER"),
        password=env("POSTGRES_PASSWORD"),
    )
    conn.autocommit = True
    with conn.cursor() as cur:
        for mv in MATERIALIZED_VIEWS:
            # CONCURRENTLY impossible tant que la vue n'a jamais été remplie
            cur.execute("SELECT ispopulated FROM pg_matviews WHERE matviewname = %s", (mv,))
            populated = cur.fetchone()[0]
            cur.execute(f"REFRESH MATERIALIZED VIEW {'CONCURRENTLY ' if populated else ''}{mv}")
            print(f"[pg] vue rafraîchie : {mv}")
    conn.close()


def main() -> None:
    spark = get_spark("publish-postgres")
    url, props = postgres_jdbc()
    for source, target in MAPPING.items():
        if not spark.catalog.tableExists(source):
            print(f"[skip] {source} n'existe pas encore (lancer dbt run)")
            continue
        df = spark.table(source)
        (
            df.write.mode("overwrite")
            .option("truncate", "true")
            .option("batchsize", 10_000)
            .jdbc(url, target, properties=props)
        )
        print(f"[pg] {source} -> {target}")
    refresh_views()
    spark.stop()


if __name__ == "__main__":
    main()
