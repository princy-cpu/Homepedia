# Stack technique Homepedia (lakehouse)

Ce document reprend la stack proposée, ajoute les briques exigées par le sujet et donne l'équivalent AWS de chaque brique.

| Ordre | Nom | Fonction | Pourquoi dans la stack | Équivalent AWS | Extensions / intégrations | Phase |
|---|---|---|---|---|---|---|
| 1 | **Sources** : DVF, BAN, IGN, Cadastre, INSEE, ADEME, Géorisques, SIRENE, avis… | Fournir les données brutes | Datasets métier : transactions, adresses, géométries, parcelles, référentiels, texte | Aucun service équivalent : sources externes. Côté AWS : **Registry of Open Data**, **AppFlow** (connecteurs SaaS), **Transfer Family** (SFTP) | GeoJSON, CSV, ZIP, API HTTP, HTML (scraping) | Cœur |
| 2 | **Ingestion Python** | Extraire et charger | Télécharge les fichiers, appelle les API, contrôle les fichiers et les pousse vers le stockage objet | Lambda, Glue Python Shell, ECS task, Batch | requests, httpx, boto3, polars, pandas, pyarrow | Cœur |
| 3 | **MinIO** ⚠️ | Stockage objet compatible S3 | Simule un data lake S3 et découple stockage et calcul | Amazon S3 | API S3, versioning, Iceberg, Spark, Trino | Cœur |
| 4 | **Bronze / Raw** | Conserver les sources originales | Rejouer le pipeline, traçabilité (`_manifest.json`) | S3 Raw Zone | CSV, CSV.gz, JSON, GeoJSON, ZIP, HTML | Cœur |
| 5 | **Parquet** | Format analytique en colonnes | Compression, lecture sélective des colonnes, performances | Parquet sur S3 | PyArrow, DuckDB, Spark, Trino, Athena | Cœur |
| 6 | **Apache Iceberg** (+ catalogue REST) | Tables lakehouse | Transactions ACID, snapshots, évolution du schéma, *time travel* | Iceberg sur S3 + **Glue Data Catalog** (ou S3 Tables) | Spark, Trino, REST Catalog, Nessie, Polaris | Cœur |
| 7 | **Silver** | Données nettoyées et normalisées | Version fiable des sources, rattachée au COG | S3 curated layer | Iceberg, Spark | Cœur |
| 8 | **Apache Spark** (cluster standalone) | Calcul distribué | **Imposé par le sujet** : gros volumes (DVF, DPE, SIRENE), jointures, K-Means MLlib | EMR Spark, Glue Spark | PySpark, Spark SQL, Iceberg, Sedona | Cœur |
| 9 | **dbt Core** (adaptateur dbt-trino) | Transformations SQL métier | Modèles gold versionnés, tests, documentation, lignage | dbt Core sur ECS/MWAA, dbt Cloud | tests, macros, dbt-utils | Cœur |
| 10 | **Gold** | Tables métier | Prix au m², indicateurs par niveau, score d'opportunité | S3 serving layer | Iceberg, marts dbt | Cœur |
| 11 | **Trino** | Moteur SQL distribué | Interroge Iceberg et PostgreSQL en SQL, et sert de moteur à dbt | Athena, Trino sur EMR | Connecteurs Iceberg et PostgreSQL | Cœur |
| 12 | ➕ **PostgreSQL + PostGIS** | **Base relationnelle** (exigée) | Couche de service indexée pour l'app, requêtes spatiales, vues matérialisées | RDS / Aurora PostgreSQL | PostGIS, pg_trgm, Trino postgres connector | Cœur |
| 13 | ➕ **MongoDB** | **Base NoSQL** (exigée) | Avis textuels, résultats NLP, JSON brut des API | DocumentDB | Index texte, agrégations | Cœur |
| 14 | ➕ **Couche NLP / ML** | **Analyse textuelle** (exigée) | Sentiment, thèmes, mots-clés ; clustering des communes | SageMaker, Comprehend | transformers, CamemBERT, BERTopic, Spark MLlib | Cœur |
| 15 | ➕ **App Streamlit** | **App interactive** (exigée) | Cartes, tableaux filtrables et exportables, score paramétrable, avis | ECS / App Runner, Amplify | Folium, pydeck, Plotly | Cœur |
| 16 | **Notebooks** | Exploration | Analyse ponctuelle, prototypes | SageMaker Studio / EMR Studio | Jupyter, DuckDB, PySpark | Cœur |
| 17 | **Superset** | BI / dashboards | Exploration SQL pour les analystes | QuickSight | Driver Trino, SQL Lab | Bonus |
| 18 | **API FastAPI** | Exposer les résultats | Consommation par un front ou des tiers | API Gateway + Lambda / ECS | GeoJSON, cache, authentification | Bonus |
| 19 | ➕ **Orchestration** (Dagster ou Airflow) | Enchaîner et planifier | Dépendances entre jobs, reprise sur erreur | MWAA, Step Functions | Capteurs, planification | Bonus |
| 20 | ➕ **Qualité des données** | Contrôles | Tests dbt, règles de validation | Glue Data Quality | dbt tests, Great Expectations | Cœur (tests dbt) |

➕ = brique ajoutée à la proposition initiale.

## Points d'attention

1. **Exigences du sujet** : Iceberg et Trino ne remplacent pas les deux bases demandées. Le sujet exige une base **relationnelle ET** une base **non relationnelle**, avec indexation. PostgreSQL et MongoDB sont donc indispensables.
2. **MinIO** : depuis le 23 octobre 2025, MinIO ne publie plus d'images Docker pour l'édition communautaire. Le projet utilise l'image gratuite `cgr.dev/chainguard/minio`. Alternatives : Garage, SeaweedFS, RustFS.
3. **Superset ne remplace pas l'app** : le sujet demande une application « highly interactive and customizable », avec les résultats de l'analyse textuelle. Streamlit reste l'app principale ; Superset est un plus pour les analystes.
4. **Charge de travail en solo** : la stack complète tourne en local avec environ 8 à 10 Go de RAM. Les services bonus sont isolés dans des *profils* Docker Compose pour ne démarrer que le nécessaire :
   - `docker compose up -d` → cœur ;
   - `docker compose --profile bi up -d` → Superset ;
   - `docker compose --profile api up -d` → FastAPI.
5. **Répartition Spark / dbt** :
   - Spark fait le travail lourd : bronze → silver (DVF, DPE, SIRENE…) et le ML.
   - dbt + Trino font la logique métier en SQL : silver → gold.
   - Les tables gold sont ensuite publiées dans PostgreSQL pour l'app.
