"""Outils partagés par les jobs Spark : session, normalisation des codes géographiques."""
from __future__ import annotations

import os
import re

# Arrondissements municipaux -> commune (Paris, Lyon, Marseille)
PLM = {
    **{f"751{i:02d}": "75056" for i in range(1, 21)},
    **{f"6938{i}": "69123" for i in range(1, 10)},
    **{f"132{i:02d}": "13055" for i in range(1, 17)},
}

_CODE_RE = re.compile(r"^(\d{5}|2[AB]\d{3})$")


def normalize_code_insee(code: str | int | None, merge_plm: bool = True) -> str | None:
    """Normalise un code commune INSEE (Python pur, testable sans Spark).

    >>> normalize_code_insee(1004)
    '01004'
    >>> normalize_code_insee('2a004')
    '2A004'
    >>> normalize_code_insee('75112')
    '75056'
    """
    if code is None:
        return None
    s = str(code).strip().upper()
    if s.endswith(".0"):          # code lu comme float par pandas
        s = s[:-2]
    if s.isdigit():
        s = s.zfill(5)
    if not _CODE_RE.match(s):
        return None
    if merge_plm:
        s = PLM.get(s, s)
    return s


def normalize_code_insee_col(col, merge_plm: bool = True):
    """Équivalent Spark (expressions natives, sans UDF Python => rapide)."""
    from pyspark.sql import functions as F

    c = F.upper(F.trim(col.cast("string")))
    c = F.regexp_replace(c, r"\.0$", "")
    c = F.when(c.rlike(r"^\d+$"), F.lpad(c, 5, "0")).otherwise(c)
    c = F.when(c.rlike(r"^(\d{5}|2[AB]\d{3})$"), c)
    if merge_plm:
        mapping = F.create_map(*[F.lit(x) for kv in PLM.items() for x in kv])
        c = F.coalesce(mapping[c], c)
    return c


def normalize_code_dep_col(col):
    from pyspark.sql import functions as F

    c = F.upper(F.trim(col.cast("string")))
    return F.when(c.rlike(r"^\d$"), F.lpad(c, 2, "0")).otherwise(c)


def get_spark(app_name: str):
    """Session Spark. La config Iceberg/S3 vient de spark-defaults.conf (cluster Docker)
    ou de la configuration du cluster (Databricks)."""
    from pyspark.sql import SparkSession

    builder = SparkSession.builder.appName(f"homepedia-{app_name}")
    # Identifiants S3 pour S3FileIO (Iceberg) lus depuis l'environnement
    if os.getenv("S3_ACCESS_KEY"):
        builder = builder.config("spark.sql.catalog.iceberg.s3.access-key-id", os.environ["S3_ACCESS_KEY"])
        builder = builder.config("spark.sql.catalog.iceberg.s3.secret-access-key", os.environ["S3_SECRET_KEY"])
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark


def latest_run_date(source: str) -> str:
    """Date (dossier) de la dernière ingestion d'une source dans le bronze."""
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT", "http://minio:9000"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    resp = s3.list_objects_v2(Bucket=os.getenv("S3_BUCKET_RAW", "raw"), Prefix=f"{source}/", Delimiter="/")
    dates = sorted(p["Prefix"].rstrip("/").split("/")[-1] for p in resp.get("CommonPrefixes", []))
    if not dates:
        raise FileNotFoundError(f"Aucune ingestion trouvée pour '{source}' : lancer download.py d'abord")
    return dates[-1]


def raw_path(source: str, pattern: str = "*", run_date: str | None = None) -> str:
    """Chemin du bronze pour une source. Par défaut : la dernière ingestion
    (évite de lire deux fois les mêmes lignes si la source a été téléchargée plusieurs fois)."""
    bucket = os.getenv("S3_BUCKET_RAW", "raw")
    run_date = run_date or latest_run_date(source)
    return f"s3a://{bucket}/{source}/{run_date}/{pattern}"
