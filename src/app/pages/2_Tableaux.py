"""Tableaux filtrables, croisement d'indicateurs et export."""
import io

import plotly.express as px
import streamlit as st

from db import NIVEAUX, departements, indicateurs_large

st.set_page_config(page_title="Tableaux · Homepedia", layout="wide")
st.title("📊 Indicateurs")

c1, c2, c3 = st.columns(3)
niveau = NIVEAUX[c1.selectbox("Niveau", list(NIVEAUX))]
annee = c2.number_input("Année", min_value=2014, max_value=2030, value=2024)
code_dep = None
if niveau == "commune":
    deps = departements()
    code_dep = c3.selectbox("Département", deps["code_dep"] + " - " + deps["nom"]).split(" - ")[0]

df = indicateurs_large(niveau, int(annee), code_dep)
if df.empty:
    st.info("Pas de données pour cette sélection.")
    st.stop()

colonnes = st.multiselect("Colonnes", [c for c in df.columns if c != "code"], default=list(df.columns[1:6]))
vue = df[["code", *colonnes]]
st.dataframe(vue, hide_index=True, use_container_width=True)

e1, e2 = st.columns(2)
e1.download_button("⬇️ CSV", vue.to_csv(index=False).encode("utf-8"), f"homepedia_{niveau}_{annee}.csv", "text/csv")
buf = io.BytesIO()
vue.to_excel(buf, index=False)
e2.download_button("⬇️ Excel", buf.getvalue(), f"homepedia_{niveau}_{annee}.xlsx")

st.subheader("Croiser deux indicateurs")
if len(colonnes) >= 2:
    x = st.selectbox("Axe X", colonnes, index=0)
    y = st.selectbox("Axe Y", colonnes, index=1)
    fig = px.scatter(vue, x=x, y=y, hover_name="code", trendline=None)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Sélectionner au moins deux colonnes.")
