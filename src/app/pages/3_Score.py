"""Score d'opportunité avec pondérations personnalisables."""
# 🔧 EXERCICE E9 (docs/06_parcours_apprentissage.md) : cette page lit l'ancienne
# structure de config/scoring.yaml (profils[...]["poids"]). À adapter aux 2 axes
# (potentiel / risque_2040) et à la table score_territoire.

import streamlit as st

from db import NIVEAUX, profils, query

st.set_page_config(page_title="Score · Homepedia", layout="wide")
st.title("🎯 Score d'opportunité")

SOUS_SCORES = ["marche", "rentabilite", "demande", "concurrence", "cadre_de_vie", "risques"]

p = profils()
c1, c2 = st.columns(2)
profil = c1.selectbox("Profil", list(p), format_func=lambda k: p[k]["label"])
niveau = NIVEAUX[c2.selectbox("Niveau", list(NIVEAUX), index=1)]

st.sidebar.header("Pondérations")
poids = {s: st.sidebar.slider(s.replace("_", " ").capitalize(), 0.0, 1.0, float(p[profil]["poids"][s]), 0.05) for s in SOUS_SCORES}
total = sum(poids.values()) or 1.0

# Les sous-scores du profil de référence sont précalculés ; on recombine ici
# avec les poids choisis par l'utilisateur (pas de nouveau calcul Spark).
df = query(
    """SELECT s.*, COALESCE(c.nom, d.nom, r.nom) AS nom
       FROM score_opportunite s
       LEFT JOIN ref_commune c ON s.niveau = 'commune' AND c.code_insee = s.code
       LEFT JOIN ref_departement d ON s.niveau = 'departement' AND d.code_dep = s.code
       LEFT JOIN ref_region r ON s.niveau = 'region' AND r.code_reg = s.code
       WHERE s.niveau = :niveau AND s.profil = :profil""",
    niveau=niveau, profil=profil,
)
if df.empty:
    st.info("Scores non calculés : lancer `dbt run` puis `publish_to_postgres`.")
    st.stop()

df["score_perso"] = sum(df[f"s_{s}"].fillna(50).astype(float) * w for s, w in poids.items()) / total
df = df.sort_values("score_perso", ascending=False)

top = st.slider("Nombre de territoires affichés", 5, 100, 20)
st.dataframe(
    df[["code", "nom", "score_perso", *[f"s_{s}" for s in SOUS_SCORES]]].head(top),
    hide_index=True,
    use_container_width=True,
    column_config={"score_perso": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f")},
)
