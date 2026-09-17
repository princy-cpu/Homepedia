# Notebooks

Exploration ponctuelle des données (profilage, prototypes de nettoyage, tests de modèles NLP).

Lancer JupyterLab dans le conteneur outils :

```bash
docker compose run --rm -p 8888:8888 tools jupyter lab --ip 0.0.0.0 --allow-root --no-browser
```

Conventions :
- `NN_sujet.ipynb` (ex. `01_profilage_dvf.ipynb`) ;
- aucun résultat volumineux commité : vider les sorties avant chaque commit ;
- une logique qui marche dans un notebook doit être déplacée dans `src/homepedia/`.
