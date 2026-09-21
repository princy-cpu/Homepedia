# Gestion de projet Homepedia

> Démarrage : lundi 21 septembre 2026. Durée prévue : 8 semaines, soit une fin autour du 13 novembre 2026.
> Adapte les dates à ta vraie date de rendu et à ton rythme d'alternance.

## Comment utiliser ce document

- **Une tâche = une case à cocher.** Coche-la quand elle est finie **et** commitée sur Git.
- Chaque tâche a un **identifiant** (exemple : `T2.3`). Réutilise-le dans tes messages de commit (`T2.3 ingestion DVF vers le bronze`) : ça relie ton historique Git à ton plan.
- **Définition de « terminé »** : le code tourne, le résultat est vérifié, et une ligne est ajoutée dans `docs/journal.md`.
- **Revue hebdomadaire** (30 minutes, le vendredi) : qu'est-ce qui est fait, qu'est-ce qui bloque, qu'est-ce qu'on décale ?

Légende de l'estimation : 🟢 moins de 2 heures, 🟡 une demi-journée, 🔴 une journée ou plus.

---

## Jalons

| Jalon | Date cible | Critère de réussite |
|---|---|---|
| **J1 : premier résultat** | Fin du jour 1 (21/09) | Prix médian au mètre carré par commune calculé à partir de DVF (Demandes de valeurs foncières), sur un département |
| **J2 : socle en place** | Fin de semaine 1 (25/09) | Infrastructure stable, DVF nettoyé dans le silver, première carte |
| **J3 : sources du cœur collectées** | Fin de semaine 2 (02/10) | Toutes les sources prioritaires P0 et P1 dans le bronze |
| **J4 : jointure ventes et diagnostics** | Fin de semaine 3 (09/10) | Ventes reliées à leur diagnostic de performance énergétique (DPE), avec taux de correspondance mesuré |
| **J5 : scores calculés** | Fin de semaine 4 (16/10) | Axes potentiel et risque 2040 calculés, publiés dans PostgreSQL |
| **J6 : intelligence artificielle** | Fin de semaine 6 (30/10) | Modèle de prix et analyse des avis documentés |
| **J7 : application complète** | Fin de semaine 7 (06/11) | Carte, matrice, tableaux, avis, exports |
| **J8 : rendu** | Fin de semaine 8 (13/11) | Exécution sur la France entière, documentation, soutenance préparée |

---

## Jour 1 : voir un premier résultat avec une seule source

**Objectif de la journée** : obtenir le prix médian au mètre carré par commune à partir de DVF, d'abord à la main dans un notebook, puis si possible via la chaîne complète (bronze, Spark, silver, Trino).

**Pourquoi DVF ?** C'est la source centrale de ta problématique : sans prix de vente, pas de potentiel de marché ni de décote. Elle est gratuite, sans compte, et donne un résultat parlant immédiatement.

**Astuce d'organisation** : la construction des images Docker prend 15 à 30 minutes. Lance-la en premier, puis travaille sur le notebook pendant qu'elle tourne.

### Matin : préparer et explorer

- [ ] **T1.1** 🟢 Créer le fichier `.env` à partir de `.env.example` et changer les mots de passe (lettres et chiffres uniquement).
- [ ] **T1.2** 🟢 Créer `.gitattributes` (contenu : `* text=auto eol=lf`) et `docs/journal.md`, puis commiter.
- [ ] **T1.3** 🟢 Pour aller vite aujourd'hui, limiter DVF à une seule année dans `config/sources.yaml` : `years: [2024]`. Les autres années viendront plus tard.
- [ ] **T1.4** 🟡 Lancer `docker compose build` puis `docker compose pull`, **et passer à T1.5 pendant que ça tourne**.
- [ ] **T1.5** 🟡 **Profilage de DVF dans un notebook** (`notebooks/01_profilage_dvf.ipynb`), sans Docker :
  - télécharger le fichier d'**un département** pour l'année 2024 (dossier `departements/` sur https://files.data.gouv.fr/geo-dvf/latest/csv/) ;
  - le lire avec pandas ou DuckDB ;
  - répondre par écrit aux 5 questions de profilage : nombre de lignes, nombre de ventes distinctes (`id_mutation`), valeurs de `nature_mutation` et `type_local`, part de valeurs manquantes, prix au mètre carré minimum et maximum.
- [ ] **T1.6** 🟡 **Premier résultat** dans le même notebook :
  - ne garder que les ventes (`nature_mutation = 'Vente'`) de maisons et d'appartements ;
  - calculer le prix au mètre carré (`valeur_fonciere / surface_reelle_bati`) ;
  - écarter les valeurs absurdes (à toi de choisir des bornes et de les justifier) ;
  - afficher le **prix médian au mètre carré par commune et par type de bien**, trié, avec le nombre de ventes.
  - ✅ **Jalon J1 atteint** si le résultat est crédible (vérifie 2 ou 3 communes que tu connais).

### Après-midi : faire passer la même donnée par la chaîne big data

- [ ] **T1.7** 🟢 `docker compose up -d`, puis vérifier chaque service (tableau de vérification donné dans la conversation : MinIO, Spark avec 2 workers, Trino, PostgreSQL, MongoDB, Streamlit).
- [ ] **T1.8** 🟢 Créer les buckets : `docker compose run --rm tools python -m homepedia.lake`.
- [ ] **T1.9** 🟡 Ingestion vers le bronze : `download api_geo dvf`. Retrouver les fichiers et un `_manifest` dans la console MinIO.
- [ ] **T1.10** 🟡 Lire et annoter `bronze_to_silver_ref_geo.py` et `bronze_to_silver_dvf.py`, puis les lancer avec `spark-submit`. Observer l'interface Spark (port 4040).
- [ ] **T1.11** 🟢 Dans Trino, écrire toi-même la requête « prix médian au mètre carré par commune » sur `iceberg.silver.dvf_mutations`.
- [ ] **T1.12** 🟢 **Contrôle croisé** : comparer le résultat Trino avec celui du notebook pour ton département. S'il y a des écarts, les expliquer (règles de nettoyage différentes ?). C'est un vrai réflexe de qualité de données.
- [ ] **T1.13** 🟢 Journal du jour, commit, push.

**Si la stack bloque l'après-midi** : pas grave, le jalon J1 est déjà atteint grâce au notebook. Note l'erreur exacte et on la résout ensemble.

---

## Plan complet par lots

### Lot 0 : cadrage ✅
- [x] **T0.1** Problématique « Acheter, vendre ou attendre ? »
- [x] **T0.2** Choix de la stack (lakehouse, extraction puis chargement puis transformation)
- [x] **T0.3** Identification et priorisation des sources

### Lot 1 : infrastructure (semaine 1)
- [ ] **T1.x** Tâches du jour 1 ci-dessus
- [ ] **T1.20** 🟡 Exercice E0 : redessiner l'architecture de mémoire, une phrase par service dans le journal
- [ ] **T1.21** 🟢 Vérifier que le catalogue Iceberg survit à un redémarrage (`docker compose restart`)
- [ ] **T1.22** 🟡 Charger les contours des départements et des communes (Admin Express) dans PostGIS
- [ ] **T1.23** 🟡 Première carte dans Streamlit : prix médian au mètre carré par département (jalon J2)

### Lot 2 : collecte des données (semaines 1 et 2)
- [ ] **T2.1** 🟡 Compléter les liens réels de `sources.yaml` pour P0 et P1
- [ ] **T2.2** 🟢 Remettre les 5 années de DVF
- [ ] **T2.3** 🟡 Ingestion DPE (diagnostics de performance énergétique, ADEME)
- [ ] **T2.4** 🟡 Ingestion BDNB (Base de données nationale des bâtiments), exports par département pour commencer
- [ ] **T2.5** 🔴 Écrire l'ingestion de l'API Géorisques (pagination, limites de débit, reprise sur erreur), exercice E1
- [ ] **T2.6** 🟡 Ingestion carte des argiles 2026, INSEE (dossier complet), Filosofi (revenus)
- [ ] **T2.7** 🔴 Scraping des avis d'habitants : adapter les sélecteurs, tester sur 10 communes, respecter `robots.txt`
- [ ] **T2.8** 🟡 Sources P2 : DRIAS (compte à créer), ONRN, trait de côte, Sitadel, équipements, gares
- [ ] **T2.9** 🟢 Remplir les fiches qualifiées des sources P2 et P3 dans `02b_priorisation_sources.md`
- [ ] **T2.10** 🟢 Petit exercice : option `--priorite` dans `download.py --list`

### Lot 3 : nettoyage et jointures, silver (semaines 2 et 3)
- [ ] **T3.1** 🟡 Compléter `04_nettoyage.md` avec les comptages de lignes DVF réels
- [ ] **T3.2** 🔴 Écrire `bronze_to_silver_dpe.py` (DPE le plus récent par logement, indicateur réforme 2026), exercice E2
- [ ] **T3.3** 🔴 **Écrire la jointure ventes × bâtiments × diagnostics** (`silver_dvf_dpe.py`), exercice E3, cœur du projet (jalon J4)
- [ ] **T3.4** 🟡 Mesurer et documenter le taux de correspondance par département
- [ ] **T3.5** 🟡 Silver des risques : arrêtés de catastrophe naturelle par commune, part de bâti exposé aux argiles (jointure spatiale)
- [ ] **T3.6** 🟡 Silver socio-économique : population, revenus, logements

### Lot 4 : modélisation et indicateurs, gold (semaine 4)
- [ ] **T4.1** 🔴 Adapter `01_schema.sql` au schéma cible, exercice E4
- [ ] **T4.2** 🟡 Prouver l'utilité d'un index avec `EXPLAIN ANALYZE` (temps avant et après dans le journal)
- [ ] **T4.3** 🔴 Transformer `gold_score_opportunite.sql` en `gold_score_territoire.sql` (2 axes et quadrant), exercice E6
- [ ] **T4.4** 🟡 Tests dbt (valeurs acceptées, bornes 0 à 100, relations)
- [ ] **T4.5** 🟡 Mettre à jour `publish_to_postgres.py` et publier (jalon J5)
- [ ] **T4.6** 🟢 Générer la documentation dbt et commenter le graphe de lignage

### Lot 5 : base documentaire MongoDB (semaine 5)
- [ ] **T5.1** 🟢 Tester la validation de schéma (insérer un document invalide)
- [ ] **T5.2** 🟡 Écrire l'agrégation « mentions d'inondation par département », exercice E5

### Lot 6 : intelligence artificielle (semaines 5 et 6)
- [ ] **T6.1** 🔴 Modèle de prix hédonique (régression linéaire sur le logarithme du prix), exercice E7
- [ ] **T6.2** 🟡 Comparer la décote estimée aux chiffres des Notaires
- [ ] **T6.3** 🟡 Modèle prédictif (arbres de décision boostés) et évaluation sur la dernière année
- [ ] **T6.4** 🟡 Analyse de sentiment des avis, puis validation sur 200 avis étiquetés à la main, exercice E8
- [ ] **T6.5** 🟡 Extraction des thèmes des avis
- [ ] **T6.6** 🟡 Typologie des communes (K-Means)
- [ ] **T6.7** 🟡 Rédiger `05_ia.md` avec les métriques (jalon J6)

### Lot 7 : application (semaines 6 et 7)
- [ ] **T7.1** 🟡 Adapter la page Score aux 2 axes, exercice E9
- [ ] **T7.2** 🔴 Page Matrice (potentiel × risque, 4 quadrants, filtre par département)
- [ ] **T7.3** 🟡 Page Segments de biens (prix par classe énergétique, type, période de construction)
- [ ] **T7.4** 🟢 Affichage « données non disponibles » pour l'Alsace-Moselle et Mayotte
- [ ] **T7.5** 🟢 Exports CSV et Excel sur toutes les pages de tableaux
- [ ] **T7.6** 🟡 Adapter l'API FastAPI (bonus) (jalon J7)

### Lot 8 : passage à la France entière (semaine 7)
- [ ] **T8.1** 🟢 Choisir l'infrastructure d'exécution nationale avec ton pédago (Databricks, machines virtuelles du campus ou local)
- [ ] **T8.2** 🔴 Exécuter tout le pipeline avec `DEV_DEPARTEMENTS` vide
- [ ] **T8.3** 🟡 Mesurer les temps (échantillon et France entière) et les noter : argument clé de la soutenance

### Lot 9 : documentation et soutenance (semaine 8)
- [ ] **T9.1** 🟡 Relire et compléter tous les documents de `docs/`
- [ ] **T9.2** 🟡 Répondre aux 8 questions de l'exercice E10 sans notes
- [ ] **T9.3** 🔴 Préparer la démonstration (scénario de 5 minutes) et les supports
- [ ] **T9.4** 🟡 Bonus éventuels : déploiement en ligne protégé, Superset, visite guidée (jalon J8)

---

## Registre des risques

| Risque | Probabilité | Impact | Parade |
|---|---|---|---|
| La stack Docker ne démarre pas du premier coup | Moyenne | Moyen | Notebook DuckDB en parallèle ; m'envoyer les messages d'erreur exacts |
| Mémoire insuffisante sur le PC | Moyenne | Élevé | Réduire la mémoire des workers, traiter par département, exécution nationale sur Databricks ou campus |
| Jointure ventes × diagnostics décevante | Élevée | Élevé | Mesurer tôt (semaine 3), documenter les limites, plan B par adresse |
| Scraping bloqué | Moyenne | Moyen | Cache local, rythme lent, source de secours |
| Retard cumulé | Moyenne | Élevé | Revue du vendredi ; couper d'abord les sources P3 et les bonus, jamais la documentation |

## Suivi hebdomadaire

| Semaine | Prévu | Fait | Bloquants | Décision |
|---|---|---|---|---|
| S1 (21/09) | Lot 1, début du lot 2 | | | |
| S2 (28/09) | Lot 2, début du lot 3 | | | |
| S3 (05/10) | Lot 3 | | | |
| S4 (12/10) | Lot 4 | | | |
| S5 (19/10) | Lots 5 et 6 | | | |
| S6 (26/10) | Lots 6 et 7 | | | |
| S7 (02/11) | Lots 7 et 8 | | | |
| S8 (09/11) | Lot 9 | | | |
