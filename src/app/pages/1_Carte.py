"""Carte choroplèthe multi-niveaux."""
import folium
import streamlit as st
from streamlit_folium import st_folium

from db import NIVEAUX, departements, geojson, indicateurs_large, liste_indicateurs

st.set_page_config(page_title="Carte · Homepedia", layout="wide")
st.title("🗺️ Carte des indicateurs")

indics = liste_indicateurs()
if not indics:
    st.info("Aucun indicateur en base : lancer le pipeline (dbt run puis publish_to_postgres).")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
niveau = NIVEAUX[c1.selectbox("Niveau", list(NIVEAUX))]
indicateur = c2.selectbox("Indicateur", indics)
annee = c3.number_input("Année", min_value=2014, max_value=2030, value=2024)
code_dep = None
if niveau == "commune":
    deps = departements()
    choix = c4.selectbox("Département", deps["code_dep"] + " - " + deps["nom"])
    code_dep = choix.split(" - ")[0]

data = indicateurs_large(niveau, int(annee), code_dep)
if data.empty or indicateur not in data:
    st.warning("Pas de données pour cette sélection.")
    st.stop()

fc = geojson(niveau, code_dep)
m = folium.Map(location=[46.6, 2.4], zoom_start=6 if niveau != "commune" else 9, tiles="cartodbpositron")
folium.Choropleth(
    geo_data=fc,
    data=data,
    columns=["code", indicateur],
    key_on="feature.properties.code",
    fill_color="YlOrRd",
    fill_opacity=0.75,
    line_opacity=0.2,
    nan_fill_color="#dddddd",
    legend_name=indicateur,
).add_to(m)
folium.GeoJson(
    fc,
    style_function=lambda _: {"fillOpacity": 0, "weight": 0},
    tooltip=folium.GeoJsonTooltip(fields=["nom", "code"], aliases=["Territoire", "Code"]),
).add_to(m)
if niveau == "commune":
    m.fit_bounds(folium.GeoJson(fc).get_bounds())

st_folium(m, use_container_width=True, height=620, returned_objects=[])
