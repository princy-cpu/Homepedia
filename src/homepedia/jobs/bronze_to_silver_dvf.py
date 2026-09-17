"""DVF : bronze (CSV.gz) -> iceberg.silver.dvf_mutations

Lancement (depuis la racine du projet) :
    docker compose exec spark-master spark-submit src/homepedia/jobs/bronze_to_silver_dvf.py

Règles de nettoyage : voir docs/04_nettoyage.md (section DVF).
"""
from __future__ import annotations

from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F

from homepedia.config import dev_departements
from homepedia.jobs.common import get_spark, normalize_code_dep_col, normalize_code_insee_col, raw_path

TABLE = "iceberg.silver.dvf_mutations"
TYPES_RETENUS = ["Maison", "Appartement"]
PRIX_M2_MIN, PRIX_M2_MAX = 300, 30_000


def log_count(df: DataFrame, step: str) -> DataFrame:
    """Compte les lignes à chaque étape (utile pour 04_nettoyage.md). Coûteux : désactiver en prod."""
    print(f"[dvf] {step:<40} {df.count():>12,} lignes")
    return df


def read_bronze(spark) -> DataFrame:
    df = (
        spark.read.option("header", True)
        .option("inferSchema", False)
        .csv(raw_path("dvf", "*.csv.gz"))
        .withColumn("_bronze_path", F.input_file_name())
    )
    deps = dev_departements()
    if deps:
        df = df.where(F.col("code_departement").isin(deps))
    return df


def clean(df: DataFrame) -> DataFrame:
    df = log_count(df, "brut")

    df = (
        df.where(F.col("nature_mutation") == "Vente")
        .withColumn("date_mutation", F.to_date("date_mutation"))
        .withColumn("valeur_fonciere", F.col("valeur_fonciere").cast("double"))
        .withColumn("surface_reelle_bati", F.col("surface_reelle_bati").cast("double"))
        .withColumn("surface_terrain", F.col("surface_terrain").cast("double"))
        .withColumn("nombre_pieces_principales", F.col("nombre_pieces_principales").cast("int"))
        .withColumn("longitude", F.col("longitude").cast("double"))
        .withColumn("latitude", F.col("latitude").cast("double"))
        .withColumn("code_insee_origine", F.col("code_commune"))
        .withColumn("code_insee", normalize_code_insee_col(F.col("code_commune")))
        .withColumn("code_departement", normalize_code_dep_col(F.col("code_departement")))
    )
    df = log_count(df, "après filtre Vente")

    # Mutations : on ne garde que celles qui portent sur UN SEUL logement
    # (sinon la valeur foncière couvre plusieurs biens et le prix/m² est faux).
    w = Window.partitionBy("id_mutation")
    df = (
        df.withColumn("nb_logements", F.sum(F.col("type_local").isin(TYPES_RETENUS).cast("int")).over(w))
        .withColumn("surface_terrain_totale", F.sum(F.coalesce("surface_terrain", F.lit(0.0))).over(w))
        .where((F.col("nb_logements") == 1) & F.col("type_local").isin(TYPES_RETENUS))
        .dropDuplicates(["id_mutation"])
    )
    df = log_count(df, "après mutations mono-logement")

    df = (
        df.where(F.col("valeur_fonciere").isNotNull() & (F.col("surface_reelle_bati") >= 9))
        .withColumn("prix_m2", F.round(F.col("valeur_fonciere") / F.col("surface_reelle_bati"), 2))
        .where(F.col("prix_m2").between(PRIX_M2_MIN, PRIX_M2_MAX))
    )
    df = log_count(df, "après bornes absolues")

    # Valeurs aberrantes : IQR par département et type de bien
    bounds = df.groupBy("code_departement", "type_local").agg(
        F.expr("percentile_approx(prix_m2, 0.25, 1000)").alias("q1"),
        F.expr("percentile_approx(prix_m2, 0.75, 1000)").alias("q3"),
    )
    df = (
        df.join(F.broadcast(bounds), ["code_departement", "type_local"])
        .withColumn("iqr", F.col("q3") - F.col("q1"))
        .where(F.col("prix_m2").between(F.col("q1") - 1.5 * F.col("iqr"), F.col("q3") + 1.5 * F.col("iqr")))
        .drop("q1", "q3", "iqr")
    )
    df = log_count(df, "après IQR")

    return df.select(
        "id_mutation",
        "date_mutation",
        F.year("date_mutation").alias("annee"),
        "valeur_fonciere",
        "type_local",
        "surface_reelle_bati",
        "nombre_pieces_principales",
        "surface_terrain_totale",
        "prix_m2",
        "code_insee",
        "code_insee_origine",
        "code_departement",
        "code_postal",
        "nom_commune",
        "id_parcelle",
        "longitude",
        "latitude",
        F.lit("dvf").alias("_source"),
        F.current_timestamp().alias("_ingested_at"),
        "_bronze_path",
    )


def write(df: DataFrame) -> None:
    spark = df.sparkSession
    spark.sql("CREATE NAMESPACE IF NOT EXISTS iceberg.silver")
    (
        df.sortWithinPartitions("code_insee")
        .writeTo(TABLE)
        .partitionedBy(F.col("annee"), F.col("code_departement"))
        .tableProperty("write.format.default", "parquet")
        .tableProperty("write.parquet.compression-codec", "zstd")
        .createOrReplace()
    )
    print(f"[dvf] table écrite : {TABLE}")


def main() -> None:
    spark = get_spark("dvf-silver")
    write(clean(read_bronze(spark)))
    spark.stop()


if __name__ == "__main__":
    main()
