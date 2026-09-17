"""Avis d'habitants analysés par IA."""
import pandas as pd
import plotly.express as px
import streamlit as st

from db import mongo

st.set_page_config(page_title="Avis · Homepedia", layout="wide")
st.title("💬 Ce que disent les habitants")

db = mongo()
code = st.text_input("Code INSEE de la commune", "69123")
synthese = db["nlp_synthese_commune"].find_one({"code_insee": code}, {"_id": 0})

if not synthese:
    st.info("Aucun avis analysé pour cette commune (scrape_avis puis nlp.sentiment).")
    st.stop()

c1, c2 = st.columns(2)
c1.metric("Avis analysés", synthese["nb_avis"])
c2.metric("Sentiment moyen (-1 à 1)", f"{synthese['sentiment_moyen']:+.2f}")

rep = pd.DataFrame(list(synthese["repartition"].items()), columns=["sentiment", "nb"])
st.plotly_chart(px.bar(rep, x="sentiment", y="nb", color="sentiment"), use_container_width=True)

if synthese.get("mentions"):
    mentions = pd.DataFrame(list(synthese["mentions"].items()), columns=["mot", "occurrences"])
    st.subheader("Mots surveillés")
    st.plotly_chart(px.bar(mentions.sort_values("occurrences"), x="occurrences", y="mot", orientation="h"),
                    use_container_width=True)

st.subheader("Recherche dans les avis")
terme = st.text_input("Mot-clé (index texte MongoDB)", "")
filtre = {"code_insee": code}
if terme:
    filtre["$text"] = {"$search": terme}
for a in db["avis"].find(filtre, {"texte": 1, "nlp.sentiment": 1}).limit(20):
    st.markdown(f"**{a.get('nlp', {}).get('sentiment', '?')}** · {a['texte'][:400]}")
