"""Référentiel géographique : bronze (API Geo JSON) -> iceberg.silver.ref_* + PostgreSQL ref_*.

    docker compose exec spark-master spark-submit src/homepedia/jobs/bronze_to_silver_ref_geo.py

À lancer en premier : toutes les autres tables s'appuient sur ce référentiel.
Les géométries sont chargées séparément par homepedia.ingestion.load_contours.
"""
from __future__ import annotations

import psycopg2
from psycopg2.extras import execute_values
from pyspark.sql import functions as F

from homepedia.config import env
from homepedia.jobs.common import get_spark, normalize_code_dep_col, raw_path


def main() -> None:
    spark = get_spark("ref-geo")
    read = lambda name: spark.read.option("multiLine", True).json(raw_path("api_geo", name))  # noqa: E731

    regions = read("api_geo_2.json").select(F.col("code").alias("code_reg"), "nom")
    deps = read("api_geo_1.json").select(
        normalize_code_dep_col(F.col("code")).alias("code_dep"),
        F.col("codeRegion").alias("code_reg"),
        "nom",
    )
    communes = read("api_geo_0.json").select(
        F.col("code").alias("code_insee"),
        "nom",
        normalize_code_dep_col(F.col("codeDepartement")).alias("code_dep"),
        F.col("codeRegion").alias("code_region"),
        F.col("population").cast("int").alias("population"),
        F.col("codesPostaux").alias("codes_postaux"),
    )

    spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.silver")
    for df, name in [(regions, "ref_region"), (deps, "ref_departement"), (communes, "ref_commune")]:
        df.writeTo(f"iceberg.silver.{name}").createOrReplace()
        print(f"[ref] iceberg.silver.{name} : {df.count()} lignes")

    # Petites tables : chargement direct dans PostgreSQL (upsert, géométries préservées)
    conn = psycopg2.connect(
        host=env("POSTGRES_HOST", "localhost"), dbname=env("POSTGRES_DB"),
        user=env("POSTGRES_USER"), password=env("POSTGRES_PASSWORD"),
    )
    with conn, conn.cursor() as cur:
        execute_values(
            cur,
            "INSERT INTO ref_region (code_reg, nom) VALUES %s "
            "ON CONFLICT (code_reg) DO UPDATE SET nom = EXCLUDED.nom",
            [tuple(r) for r in regions.collect()],
        )
        execute_values(
            cur,
            "INSERT INTO ref_departement (code_dep, code_reg, nom) VALUES %s "
            "ON CONFLICT (code_dep) DO UPDATE SET code_reg = EXCLUDED.code_reg, nom = EXCLUDED.nom",
            [tuple(r) for r in deps.collect()],
        )
        execute_values(
            cur,
            "INSERT INTO ref_commune (code_insee, nom, code_dep, population, codes_postaux) VALUES %s "
            "ON CONFLICT (code_insee) DO UPDATE SET nom = EXCLUDED.nom, code_dep = EXCLUDED.code_dep, "
            "population = EXCLUDED.population, codes_postaux = EXCLUDED.codes_postaux",
            [(r.code_insee, r.nom, r.code_dep, r.population, r.codes_postaux) for r in communes.collect()],
        )
    conn.close()
    print("[ref] PostgreSQL à jour")
    spark.stop()


if __name__ == "__main__":
    main()
