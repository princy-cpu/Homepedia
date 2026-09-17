"""Homepedia : page d'accueil."""
import streamlit as st

st.set_page_config(page_title="Homepedia", page_icon="🏠", layout="wide")

st.title("Homepedia")
st.subheader("Où implanter une agence ou investir dans l'immobilier en France ?")

st.markdown(
    """
Homepedia croise **prix réels (DVF)**, **loyers**, **démographie**, **concurrence**,
**cadre de vie**, **risques** et **avis d'habitants analysés par IA** pour calculer
un **score d'opportunité** aux échelles région, département et commune.

| Page | Contenu |
|---|---|
| 🗺️ **Carte** | Carte choroplèthe de n'importe quel indicateur |
| 📊 **Tableaux** | Indicateurs filtrables, triables et exportables (CSV / Excel) |
| 🎯 **Score** | Score d'opportunité avec pondérations ajustables par profil |
| 💬 **Avis** | Sentiment et thèmes des avis d'habitants |
"""
)

with st.expander("État des bases"):
    try:
        from db import query

        st.dataframe(
            query(
                """SELECT relname AS table, n_live_tup AS lignes
                   FROM pg_stat_user_tables ORDER BY relname"""
            ),
            hide_index=True,
        )
    except Exception as exc:  # base pas encore démarrée
        st.warning(f"PostgreSQL injoignable : {exc}")
