# Parcours d'apprentissage Homepedia

> **Objectif** : mener le projet à bien **en comprenant** chaque notion big data, au point de pouvoir l'expliquer et la défendre en soutenance, et pas seulement de la faire tourner.

## Comment on travaille ensemble

| Principe | En pratique |
|---|---|
| **Tu écris le code métier** | Claude ne livre plus de solution complète pour les exercices, sauf si tu la demandes explicitement après avoir essayé. |
| **Aide graduée** | 1️⃣ une question pour te guider → 2️⃣ un indice → 3️⃣ l'explication du concept → 4️⃣ un exemple minimal *sur un autre cas* → 5️⃣ la solution (en dernier recours). Dis-moi le niveau d'aide que tu veux. |
| **Relecture de code** | Quand un exercice est fini, demande « relis mon code ». Tu recevras des remarques et des questions, pas une réécriture. |
| **Comprendre avant d'exécuter** | Avant de lancer un job, écris en 3 lignes ce que tu penses qu'il va faire. Ensuite, compare avec le résultat. |
| **Journal d'apprentissage** | Tiens `docs/journal.md` à jour : ce que tu as appris, ce qui t'a bloqué, les chiffres obtenus. C'est une mine d'or pour la soutenance. |

## Ce qui existe déjà et ce qui reste à faire

| Statut | Fichiers | Ton travail |
|---|---|---|
| 📖 **Fourni : à lire et à savoir expliquer** | `docker-compose.yml`, `docker/*`, `lake.py`, `ingestion/download.py`, `jobs/common.py`, `jobs/bronze_to_silver_dvf.py`, `jobs/bronze_to_silver_ref_geo.py` | Annoter chaque bloc (commentaires `# Je comprends :`) et répondre aux questions des exercices |
| 🔧 **À adapter** (écrit pour la première problématique) | `db/postgres/init/01_schema.sql`, `dbt/models/gold/gold_score_opportunite.sql`, `src/app/pages/3_Score.py`, `src/homepedia/api/main.py`, `jobs/publish_to_postgres.py` | Les mettre en cohérence avec la nouvelle problématique (E4, E6, E9) |
| ✍️ **À écrire toi-même** | Ingestion Géorisques, silver DPE, jointure DVF × DPE, indicateurs climat, modèle hédonique, NLP complet, page « matrice » | Exercices E1 à E9 |

---

## E0 — Comprendre l'architecture *(semaine 1)*

**Notions** : data lake / data warehouse / lakehouse ; stockage objet (S3) ; séparation du stockage et du calcul ; formats orientés colonnes ; architecture médaillon (bronze / silver / gold).

**À faire**
1. Dessine le pipeline **de mémoire**, sur papier, puis compare-le à `03_architecture.md`.
2. Lance `docker compose up -d` et ouvre chaque interface (Spark, MinIO, Trino). Pour chaque conteneur, écris une phrase sur son rôle.
3. Dans la console MinIO, dépose un CSV. Convertis-le en Parquet avec pandas ou DuckDB, puis compare la taille des deux fichiers et le temps de lecture d'une seule colonne.

**Questions pour vérifier ta compréhension**
- Pourquoi le Parquet est-il plus rapide que le CSV pour `SELECT avg(prix) FROM ventes` ?
- Qu'apporte Iceberg par rapport à un simple dossier de fichiers Parquet ? (Indices : transactions ACID, snapshots, *time travel*, évolution du schéma.)
- Pourquoi garder le bronze intact, alors qu'on a déjà le silver ?
- Pourquoi séparer le stockage (MinIO) du calcul (Spark) ?

**Ressources** : [Iceberg, introduction](https://iceberg.apache.org/docs/latest/) · *Fundamentals of Data Engineering* (Reis & Housley), chapitres sur le stockage et l'architecture.

---

## E1 — Ingestion et traçabilité *(semaines 1-2)*

**Notions** : idempotence ; reprise sur erreur (*retry*, *backoff*) ; manifestes et lignage ; pagination d'API ; limites de débit.

**À faire**
1. Complète les `urls: []` de `config/sources.yaml` pour DVF, DPE, BDNB (tes départements de test) et l'argile.
2. Lis `download.py` et `lake.py`. Explique ce qui se passe si on relance deux fois le même téléchargement.
3. ✍️ **Écris** l'ingestion de l'**API Géorisques** (`type: api`), avec :
   - pagination ;
   - enregistrement du JSON brut dans MongoDB (`raw_api`) et dans le bronze ;
   - reprise en cas d'erreur 429 (trop de requêtes).

**Questions**
- Qu'est-ce qu'un traitement idempotent, et pourquoi est-ce vital dans un pipeline ?
- Pourquoi stocker le JSON brut d'une API au lieu de le transformer tout de suite ?

---

## E2 — Les fondamentaux de Spark *(semaines 2-3)*

**Notions** : driver / executors / cluster manager ; DataFrame ; **évaluation paresseuse** ; transformations *narrow* ou *wide* ; **shuffle** ; partitions ; DAG, stages et tasks ; Spark UI ; Adaptive Query Execution.

**À faire**
1. Lis `bronze_to_silver_dvf.py` et annote chaque étape.
2. Lance-le sur 1 département, puis 3, puis 10. Dans la **Spark UI** (port 4040), repère :
   - les stages ;
   - les shuffles (à cause de quelles opérations ?) ;
   - la durée de chaque étape.
3. Arrête un worker (`docker compose stop spark-worker-2`), relance le job et compare les temps.
4. Pourquoi `log_count()` coûte-t-il cher ? Vérifie en le désactivant.
5. ✍️ **Écris** `bronze_to_silver_dpe.py` en suivant les règles de `04_nettoyage.md` (DPE le plus récent par logement, drapeau réforme 2026).

**Questions**
- Quelle différence entre `df.count()` et `df.where(...)` du point de vue de l'exécution ?
- Pourquoi une *window function* `partitionBy("id_mutation")` provoque-t-elle un shuffle ?
- Comment choisir le nombre de partitions ? Que change `spark.sql.shuffle.partitions` ?

**Ressources** : [Spark SQL guide](https://spark.apache.org/docs/latest/sql-programming-guide.html) · [Spark, optimisation des performances](https://spark.apache.org/docs/latest/sql-performance-tuning.html) · *Learning Spark, 2nd ed.* (O'Reilly), chapitres 1 à 7.

---

## E3 — Jointures à grande échelle *(semaine 3)* ⭐ cœur technique du projet

**Notions** : *broadcast join* ou *sort-merge join* ; données déséquilibrées (*skew* : une clé très fréquente, comme Paris) ; qualité d'une jointure (taux de correspondance) ; jointure temporelle (le DPE le plus proche de la date de vente).

**À faire** (✍️ `silver_dvf_dpe.py`)
1. Explore la BDNB dans un notebook et trouve les tables qui relient parcelle → bâtiment → DPE.
2. Écris la jointure. Mesure le **taux de correspondance** par département et par type de bien, puis reporte-le dans `04_nettoyage.md`.
3. Compare le plan d'exécution (`df.explain()`) avec et sans `F.broadcast(...)`.
4. Ajoute la règle « pas de DPE établi plus de 2 ans après la vente » et explique pourquoi elle évite une fuite d'information.

**Questions**
- Quand Spark choisit-il automatiquement un *broadcast join* ?
- Comment détecter un *skew* dans la Spark UI, et comment le corriger (AQE, *salting*) ?

---

## E4 — Modélisation relationnelle et optimisation *(semaine 4)*

**Notions** : normalisation ; modèle en étoile ; format long ou large ; index B-tree, GIN et GIST ; vues matérialisées ; `EXPLAIN ANALYZE`.

**À faire**
1. 🔧 Adapte `01_schema.sql` au **schéma cible** de `03_architecture.md` : `fact_energie`, `fact_climat`, `fact_segment_bien`, `valeur_verte`, `score_territoire`.
2. Charge des données, puis **prouve** l'utilité d'un index : lance `EXPLAIN ANALYZE` avant et après sa création, et note les temps dans ton journal.
3. Écris une requête PostGIS : « communes à moins de 20 km d'une commune donnée, avec un risque 2040 plus faible ».

**Questions**
- Pourquoi une table d'indicateurs en format long ? Quels en sont les inconvénients ?
- Quand préférer une vue matérialisée à une vue simple ?

**Ressources** : [PostgreSQL, utiliser EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html) · [Index PostgreSQL](https://www.postgresql.org/docs/current/indexes.html) · [Documentation PostGIS](https://postgis.net/documentation/).

---

## E5 — NoSQL (MongoDB) *(semaine 5)*

**Notions** : modèle orienté documents ; schéma flexible et validation ; index texte ; pipeline d'agrégation ; quand choisir le NoSQL plutôt que le SQL.

**À faire**
1. Lis `db/mongo/init/01_init.js`, puis insère un document invalide et observe le refus.
2. ✍️ Écris une agrégation : « nombre de mentions d'inondation dans les avis, par département ».
3. Écris la même analyse en SQL, en imaginant les avis stockés dans PostgreSQL, puis compare les deux approches.

**Question** : pourquoi les avis sont-ils dans MongoDB et les indicateurs dans PostgreSQL ?

**Ressources** : [MongoDB, agrégations](https://www.mongodb.com/docs/manual/aggregation/).

---

## E6 — ELT avec dbt et Trino *(semaine 4)*

**Notions** : ETL ou ELT ; modèles, sources et `ref()` ; lignage ; tests de données ; matérialisations ; moteur SQL fédéré.

**À faire**
1. Lance `dbt docs generate` puis `dbt docs serve`, et commente le graphe de lignage.
2. 🔧 Transforme `gold_score_opportunite.sql` en **`gold_score_territoire.sql`**, avec :
   - les 2 axes (potentiel et risque 2040), calculés à partir de `config/scoring.yaml` ;
   - le quadrant ;
   - des tests dbt (valeurs acceptées pour `quadrant`, bornes 0-100).
3. Dans Trino, écris une requête qui **joint Iceberg et PostgreSQL** dans la même instruction.

**Questions**
- Pourquoi faire le silver avec Spark et le gold avec dbt/Trino ?
- Que teste `relationships` dans dbt ?

**Ressources** : [dbt, bien démarrer](https://docs.getdbt.com/docs/introduction) · [Trino, connecteur Iceberg](https://trino.io/docs/current/connector/iceberg.html).

---

## E7 — Machine learning distribué *(semaine 5)*

**Notions** : pipeline MLlib ; *feature engineering* ; variable cible en logarithme ; variables indicatrices et modalité de référence ; séparation temporelle des jeux d'entraînement et de test ; fuite d'information ; interprétation des coefficients ; GBT ; métriques RMSE et MAPE.

**À faire** (✍️ `ml/modele_hedonique.py`)
1. Régression linéaire sur `log(prix_m2)` : extrais la décote G par rapport à D, par région et par type de bien.
2. Compare tes résultats aux chiffres des Notaires (maison −25 %, appartement −12 %) et explique les écarts.
3. Entraîne un GBT, évalue-le sur la dernière année et compare-le à la régression.

**Questions**
- Pourquoi un coefficient β sur `log(prix)` se lit-il comme ≈ un pourcentage ?
- Pourquoi une séparation temporelle plutôt qu'aléatoire ?
- Corrélation ou causalité : que peut-on vraiment affirmer ?

**Ressources** : [Guide Spark MLlib](https://spark.apache.org/docs/latest/ml-guide.html).

---

## E8 — NLP *(semaine 6)*

**Notions** : tokenisation ; modèles Transformers pré-entraînés ; classification *zero-shot* ; évaluation (précision, rappel, matrice de confusion) ; biais des données textuelles.

**À faire**
1. Étiquette à la main 200 avis, puis évalue le modèle de sentiment dessus.
2. ✍️ Ajoute l'extraction de thèmes dans `nlp/sentiment.py` (partie `themes: []`).

**Ressources** : [Hugging Face, cours NLP](https://huggingface.co/learn/nlp-course).

---

## E9 — Visualisation et application *(semaines 6-7)*

**Notions** : choix du bon graphique ; échelles de couleur (séquentielle ou divergente) ; interaction ; mise en cache.

**À faire**
1. 🔧 `3_Score.py` lit encore l'ancienne structure de `scoring.yaml` (`poids`) : adapte la page aux 2 axes et aux profils.
2. ✍️ Crée la page **« Matrice »** : nuage de points potentiel × risque, 4 quadrants colorés, filtre par département.
3. ✍️ Crée la page **« Segments de biens »** : prix par classe DPE × type × période de construction.

---

## E10 — Préparer la soutenance

Tu dois pouvoir répondre sans notes :

1. Présenter la problématique et les utilisateurs en 1 minute.
2. Suivre une vente DVF du bronze jusqu'à la carte.
3. Justifier chaque brique de la stack et citer une alternative.
4. Montrer la Spark UI et expliquer un shuffle.
5. Donner le taux de correspondance DVF × DPE et ses limites.
6. Expliquer le modèle hédonique et comment tu l'as validé.
7. Expliquer pourquoi la « valeur à risque 2040 » est un scénario et non une prévision.
8. Citer 3 biais de tes données.

## Suivi

| Exercice | Statut | Date | Notes |
|---|---|---|---|
| E0 Architecture | ☐ | | |
| E1 Ingestion | ☐ | | |
| E2 Spark | ☐ | | |
| E3 Jointures | ☐ | | |
| E4 SQL | ☐ | | |
| E5 NoSQL | ☐ | | |
| E6 dbt / Trino | ☐ | | |
| E7 ML | ☐ | | |
| E8 NLP | ☐ | | |
| E9 App | ☐ | | |
| E10 Soutenance | ☐ | | |
