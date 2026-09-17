"""Chargement des contours (GeoJSON / GPKG) dans PostGIS, avec géométrie simplifiée.

    docker compose run --rm tools python -m homepedia.ingestion.load_contours \
        --niveau commune --fichier data/contours/communes.geojson --champ-code code

Source conseillée : "Contours des communes de France simplifié" (data.gouv.fr)
ou Admin Express COG (IGN). Le référentiel doit déjà être chargé
(bronze_to_silver_ref_geo) : on ne fait que mettre à jour les géométries.
"""
from __future__ import annotations

import argparse

import geopandas as gpd
import psycopg2
from psycopg2.extras import execute_values

from homepedia.config import env

TABLES = {
    "commune": ("ref_commune", "code_insee"),
    "departement": ("ref_departement", "code_dep"),
    "region": ("ref_region", "code_reg"),
}
# Tolérance de simplification en degrés (~ 100 m pour les communes)
TOLERANCE = {"commune": 0.001, "departement": 0.005, "region": 0.01}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--niveau", choices=TABLES, required=True)
    p.add_argument("--fichier", required=True)
    p.add_argument("--champ-code", required=True, help="colonne contenant le code INSEE / dep / reg")
    args = p.parse_args()

    table, key = TABLES[args.niveau]
    gdf = gpd.read_file(args.fichier).to_crs(4326)
    gdf = gdf.dissolve(by=args.champ_code).reset_index()   # regroupe les multi-parties
    rows = [(r[args.champ_code], r.geometry.wkb_hex) for _, r in gdf.iterrows()]

    conn = psycopg2.connect(
        host=env("POSTGRES_HOST", "localhost"), dbname=env("POSTGRES_DB"),
        user=env("POSTGRES_USER"), password=env("POSTGRES_PASSWORD"),
    )
    with conn, conn.cursor() as cur:
        cur.execute("CREATE TEMP TABLE tmp_geom (code TEXT, wkb TEXT) ON COMMIT DROP")
        execute_values(cur, "INSERT INTO tmp_geom VALUES %s", rows, page_size=1000)
        centroid = ", centroid = ST_PointOnSurface(g.geom)" if args.niveau == "commune" else ""
        cur.execute(
            f"""
            WITH g AS (
                SELECT code, ST_Multi(ST_CollectionExtract(
                    ST_MakeValid(ST_GeomFromWKB(decode(wkb, 'hex'), 4326)), 3)) AS geom
                FROM tmp_geom
            )
            UPDATE {table} t
            SET geom = g.geom,
                geom_simple = ST_Multi(ST_SimplifyPreserveTopology(g.geom, %s)){centroid}
            FROM g WHERE t.{key} = g.code
            """,
            (TOLERANCE[args.niveau],),
        )
        print(f"[contours] {cur.rowcount} {args.niveau}s mis à jour")
    conn.close()


if __name__ == "__main__":
    main()
