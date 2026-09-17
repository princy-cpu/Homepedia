"""Accès au data lake MinIO (API S3) : buckets, dépôt de fichiers bruts, manifestes."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from homepedia.config import env

RAW_BUCKET = env("S3_BUCKET_RAW", "raw")
WAREHOUSE_BUCKET = env("S3_BUCKET_WAREHOUSE", "warehouse")


def s3_client():
    return boto3.client(
        "s3",
        endpoint_url=env("S3_ENDPOINT", "http://localhost:9000"),
        aws_access_key_id=env("S3_ACCESS_KEY"),
        aws_secret_access_key=env("S3_SECRET_KEY"),
        region_name=env("AWS_REGION", "us-east-1"),
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_buckets() -> None:
    """Crée les buckets raw et warehouse s'ils n'existent pas (idempotent)."""
    s3 = s3_client()
    for bucket in (RAW_BUCKET, WAREHOUSE_BUCKET):
        try:
            s3.head_bucket(Bucket=bucket)
        except ClientError:
            s3.create_bucket(Bucket=bucket)
            print(f"[lake] bucket créé : {bucket}")
    # Versioning sur le bronze : on garde l'historique des fichiers sources
    s3.put_bucket_versioning(
        Bucket=RAW_BUCKET, VersioningConfiguration={"Status": "Enabled"}
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_raw(local_path: Path, source: str, url: str, run_date: str | None = None) -> str:
    """Dépose un fichier dans raw/<source>/<date>/ avec son manifeste. Retourne la clé S3."""
    run_date = run_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prefix = f"{source}/{run_date}"
    key = f"{prefix}/{local_path.name}"
    s3 = s3_client()
    s3.upload_file(str(local_path), RAW_BUCKET, key)

    manifest = {
        "source": source,
        "url": url,
        "file": local_path.name,
        "size_bytes": local_path.stat().st_size,
        "sha256": sha256_file(local_path),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=f"{prefix}/_manifest_{local_path.name}.json",
        Body=json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return f"s3a://{RAW_BUCKET}/{key}"


if __name__ == "__main__":
    ensure_buckets()
