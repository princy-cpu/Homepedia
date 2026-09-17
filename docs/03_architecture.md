# Architecture technique

> La stack détaillée, avec les équivalents AWS, se trouve dans [`00_stack.md`](00_stack.md).

## Vue d'ensemble

```mermaid
flowchart LR
    subgraph SRC[Sources]
        S1[Open data CSV / ZIP / GeoJSON]
        S2[API : Géorisques, Geo, DPE]
        S3[Sites d'avis]
    end
    ING[Ingestion Python<br/>download.py / scrape_avis.py]
    subgraph LAKE["MinIO (S3)"]
        B[(raw/ : bronze<br/>fichiers bruts)]
        SI[(warehouse/silver<br/>tables Iceberg)]
        GO[(warehouse/gold<br/>tables Iceberg)]
    end
    CAT[Iceberg REST catalog]
    SP[Spark cluster<br/>master + 2 workers]
    DBT[dbt Core]
    TR[Trino]
    PG[(PostgreSQL + PostGIS<br/>couche de service)]
    MG[(MongoDB<br/>avis + NLP)]
    NLP[NLP / ML<br/>sentiment, thèmes, K-Means]
    APP[Streamlit]
    SUP[Superset - bonus]
    API[FastAPI - bonus]

    S1 --> ING
    S2 --> ING
    S3 --> ING
    ING --> B
    ING --> MG
    B --> SP --> SI
    SP -. métadonnées .- CAT
    TR -. métadonnées .- CAT
    SI --> TR
    DBT -->|modèles SQL| TR --> GO
    GO --> SP -->|JDBC| PG
    MG --> NLP --> MG
    NLP --> PG
    PG --> APP
    MG --> APP
    TR --> SUP
    PG --> API
```

### Rôle de chaque couche

| Couche | Emplacement | Écrit par | Contenu |
|---|---|---|---|
| **Bronze** | `s3://raw/<source>/<date>/` | Ingestion Python | Fichiers originaux + `_manifest.json` (URL, date, hash) |
| **Silver** | `iceberg.silver.*` | Spark | Données typées, dédoublonnées, filtrées, rattachées au COG |
| **Gold** | `iceberg.gold.*` | dbt via Trino | Indicateurs multi-niveaux, score d'opportunité |
| **Service** | PostgreSQL `public.*` | Spark (JDBC) | Copie indexée des tables gold et des géométries, pour l'app |
| **Texte** | MongoDB `homepedia.*` | Scraper + NLP | Avis, sentiment, thèmes |

## Pourquoi PostgreSQL en plus d'Iceberg ?

- **Exigence du sujet** : une base relationnelle *et* une base non relationnelle, avec indexation et optimisation.
- **Latence** : Trino est conçu pour les requêtes analytiques, pas pour des dizaines de petites requêtes interactives. Une copie indexée dans PostgreSQL rend l'app fluide.
- **Géographie** : PostGIS gère les contours, la simplification des géométries et les requêtes « communes à moins de 20 km ».

## Schéma relationnel cible (PostgreSQL)

> Ce schéma reflète la problématique **achat/vente × risque climatique × DPE**.
> Le fichier `db/postgres/init/01_schema.sql` date de la première version (loyers, concurrence). **L'adapter à ce schéma est l'exercice E4** du [parcours d'apprentissage](06_parcours_apprentissage.md).

```mermaid
erDiagram
    ref_region ||--o{ ref_departement : contient
    ref_departement ||--o{ ref_commune : contient
    ref_commune ||--o{ fact_marche : a
    ref_commune ||--o{ fact_segment_bien : a
    ref_commune ||--o{ fact_socio_eco : a
    ref_commune ||--o{ fact_attractivite : a
    ref_commune ||--|| fact_energie : a
    ref_commune ||--|| fact_climat : a
    ref_region ||--o{ valeur_verte : a
    ref_commune ||--o| dim_cluster : appartient

    ref_commune { char code_insee PK
                  varchar code_dep FK
                  text nom
                  int population
                  geometry geom }
    fact_marche { char code_insee FK
                  smallint annee
                  text type_local
                  int nb_ventes
                  numeric prix_m2_median
                  numeric ventes_pour_1000_logements }
    fact_segment_bien { char code_insee FK
                        smallint annee
                        text type_local
                        char classe_dpe
                        text periode_construction
                        int nb_ventes
                        numeric prix_m2_median }
    fact_energie { char code_insee FK
                   int nb_dpe
                   numeric part_dpe_fg
                   numeric part_dpe_e
                   numeric part_ventes_fg }
    fact_climat { char code_insee FK
                  int nb_catnat_10ans
                  numeric part_bati_argiles_fort
                  boolean zone_inondable_ppr
                  boolean littoral_expose
                  numeric jours_35c_tracc27
                  numeric secheresse_sols_tracc27 }
    valeur_verte { char code_reg FK
                   text type_local
                   char classe_dpe
                   numeric decote_pct
                   numeric ic_bas
                   numeric ic_haut }
    score_territoire { text niveau
                       text code
                       text profil
                       numeric score_potentiel
                       numeric score_risque_2040
                       text quadrant
                       numeric valeur_a_risque_m2 }
```

- **`fact_segment_bien`** répond à « quels biens » : prix par type × classe DPE × période de construction.
- **`valeur_verte`** stocke les sorties du modèle hédonique (voir `05_ia.md`).
- **`score_territoire`** remplace `score_opportunite` : 2 axes (potentiel / risque), un quadrant et la valeur à risque.

### Optimisations
- **Côté lakehouse** :
  - tables Iceberg partitionnées, par exemple `silver.dvf_mutations` par `annee` et `code_departement` ;
  - compaction régulière avec `rewrite_data_files` ;
  - tri `ORDER BY code_insee` pour améliorer le *data skipping*.
- **Côté PostgreSQL** :
  - index B-tree composites `(code_insee, annee)` ;
  - index GIST sur les géométries ;
  - vues matérialisées par niveau ;
  - table `indicateur_territoire` en format long, pour afficher n'importe quel indicateur sans modifier le code ;
  - géométries simplifiées pour l'affichage.
- **Côté MongoDB** : index sur `code_insee` et `nlp.sentiment`, et index **texte** en langue française.

## Modèle documentaire (MongoDB)

```js
// avis
{ _id, code_insee: "69123", source: "ville-ideale", url, date_avis, date_collecte,
  notes: { environnement: 7, transports: 8, securite: 5 },
  texte: "Quartier vivant mais bruyant le soir...",
  nlp: { sentiment: "positif", score: 0.81, themes: ["transports", "bruit"], mots_cles: ["bruit"] } }

// nlp_synthese_commune
{ code_insee, nb_avis, sentiment_moyen, repartition: { positif, neutre, negatif },
  top_themes: [...], mentions: { bruit: 12, insecurite: 3 } }

// raw_api : réponses JSON brutes (Géorisques…)
```

## Services Docker

| Service | Image | Port(s) | Profil |
|---|---|---|---|
| minio | `cgr.dev/chainguard/minio` | 9000 (S3), 9001 (console) | cœur |
| iceberg-rest | `apache/iceberg-rest-fixture` | 8181 | cœur |
| spark-master | `docker/spark` (basé sur `apache/spark:3.5.9-java17-python3`) | 8080 (UI), 7077 | cœur |
| spark-worker-1/2 | idem | 8081, 8082 | cœur |
| trino | `trinodb/trino` | 8085 | cœur |
| postgres | `postgis/postgis:16-3.4` | 5432 | cœur |
| mongo | `mongo:7` | 27017 | cœur |
| app (Streamlit) | `docker/python` | 8501 | cœur |
| tools (ingestion, dbt, NLP) | `docker/python` | — | cœur (lancé à la demande) |
| superset | `docker/superset` | 8088 | `bi` |
| api (FastAPI) | `docker/python` | 8000 | `api` |

Les jobs Spark sont soumis depuis `spark-master`, qui sert de driver : la version de Python est ainsi la même sur le driver et sur les workers.
Le code ne dépend que des variables d'environnement (`S3_ENDPOINT`, `ICEBERG_URI`…). Il est donc portable vers Databricks ou EMR.
