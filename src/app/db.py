"""Accès aux données pour l'app Streamlit (avec cache)."""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from homepedia.config import mongo_uri, postgres_url, scoring

NIVEAUX = {"Région": "region", "Département": "departement", "Commune": "commune"}


@st.cache_resource
def engine():
    return create_engine(postgres_url(), pool_pre_ping=True)


@st.cache_resource
def mongo():
    return MongoClient(mongo_uri())["homepedia"]


@st.cache_data(ttl=600)
def query(sql: str, **params) -> pd.DataFrame:
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


@st.cache_data(ttl=3600)
def liste_indicateurs() -> list[str]:
    df = query("SELECT DISTINCT indicateur FROM indicateur_territoire ORDER BY 1")
    return df["indicateur"].tolist()


@st.cache_data(ttl=3600)
def departements() -> pd.DataFrame:
    return query("SELECT code_dep, nom FROM ref_departement ORDER BY code_dep")


@st.cache_data(ttl=3600)
def indicateurs_large(niveau: str, annee: int, code_dep: str | None = None) -> pd.DataFrame:
    """Indicateurs en format large (une colonne par indicateur) pour les tableaux."""
    sql = """
        SELECT i.code, i.indicateur, i.valeur
        FROM indicateur_territoire i
        {join}
        WHERE i.niveau = :niveau AND i.annee = :annee {filtre}
    """
    join, filtre = "", ""
    if niveau == "commune" and code_dep:
        join = "JOIN ref_commune c ON c.code_insee = i.code"
        filtre = "AND c.code_dep = :code_dep"
    df = query(sql.format(join=join, filtre=filtre), niveau=niveau, annee=annee, code_dep=code_dep)
    if df.empty:
        return df
    return df.pivot_table(index="code", columns="indicateur", values="valeur").reset_index()


@st.cache_data(ttl=3600)
def geojson(niveau: str, code_dep: str | None = None) -> dict:
    """Contours simplifiés en GeoJSON (FeatureCollection) générés par PostGIS."""
    table, key = {
        "region": ("ref_region", "code_reg"),
        "departement": ("ref_departement", "code_dep"),
        "commune": ("ref_commune", "code_insee"),
    }[niveau]
    where = "WHERE code_dep = :code_dep" if niveau == "commune" and code_dep else ""
    sql = f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(json_build_object(
                'type', 'Feature',
                'id', {key},
                'properties', json_build_object('code', {key}, 'nom', nom),
                'geometry', ST_AsGeoJSON(COALESCE(geom_simple, geom), 5)::json
            )), '[]'::json)
        ) AS fc
        FROM {table} {where}
    """
    df = query(sql, code_dep=code_dep)
    fc = df.iloc[0, 0]
    return fc if isinstance(fc, dict) else json.loads(fc)


def profils() -> dict:
    return scoring()["profils"]
