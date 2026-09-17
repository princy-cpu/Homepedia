# Homepedia — Document de cadrage

## 1. Problématique

> **Acheter, vendre ou attendre ?**
> Quels territoires et quels types de biens offrent le meilleur potentiel à l'achat, et lesquels risquent de perdre de la valeur d'ici 2040 sous l'effet des risques climatiques et de la faible performance énergétique (passoires thermiques) ?

Homepedia croise deux axes, calculés pour chaque commune, département et région :

- **Potentiel de marché** : dynamisme des ventes et des prix, demande, attractivité, accessibilité.
- **Risque de décote à 2040** : risque énergétique (DPE) et risque climatique, actuel et projeté.

Ces deux axes forment une **matrice de décision** :

| | **Risque 2040 faible** | **Risque 2040 élevé** |
|---|---|---|
| **Potentiel élevé** | 🟢 **Valeurs sûres** : acheter | 🟠 **Opportunités sous conditions** : acheter avec une décote négociée et un budget de rénovation ou d'adaptation |
| **Potentiel faible** | 🔵 **Marchés stables** : patrimonial, peu de plus-value | 🔴 **Zones de décote** : vendre tôt ou éviter |

La question « **quels biens** » est traitée par segment : type (maison / appartement) × classe DPE × période de construction. Pour chaque segment, l'app affiche le prix au m² et l'écart de prix entre classes DPE (la « valeur verte ») propres au territoire.

### Pourquoi l'horizon 2040 (15 ans) ?
- **Climat** : la France a adopté officiellement, le 26 janvier 2026, une **trajectoire de réchauffement de référence (TRACC)** : +2 °C en 2030, +2,7 °C en 2050 et +4 °C en 2100 par rapport à l'ère préindustrielle. Les indicateurs climatiques projetés (DRIAS) sont disponibles par niveau de réchauffement ; 2040 se situe entre +2 °C et +2,7 °C.
- **Énergie** : le calendrier de la loi Climat et Résilience interdit de mettre en location les logements classés G depuis 2025, F en 2028 et E en 2034. Les propriétaires bailleurs de passoires sont donc incités à vendre, ce qui pèse sur les prix. Selon les Notaires (données 2024, publiées fin 2025), une maison classée G se vend environ **25 % moins cher** qu'une maison classée D, et un appartement G environ **12 % moins cher**. Les biens classés E, F ou G représentent environ 40 % des ventes.
- **Point de vigilance** : depuis le 1er janvier 2026, le coefficient de l'électricité dans le calcul du DPE est passé de 2,3 à 1,9. Environ 850 000 logements chauffés à l'électricité sont ainsi sortis du statut de passoire. Les DPE antérieurs doivent être interprétés avec prudence (voir `04_nettoyage.md`).

## 2. Utilisateurs cibles

| Persona | Question métier | Ce que Homepedia lui apporte |
|---|---|---|
| **Acheteur investisseur / marchand de biens** | « Où acheter pour que mon bien garde ou prenne de la valeur ? » | Matrice potentiel × risque, valeur verte locale, segments sous-évalués |
| **Agence immobilière / réseau** | « Comment conseiller mes vendeurs et mes acheteurs sur les prix ? » | Prix par segment, décote DPE locale, liquidité du marché |
| **Banque / assureur** | « Quelle sera la valeur de la garantie dans 15 ans ? » | Valeur à risque 2040, exposition climatique, part de passoires dans les ventes |
| **Collectivité** *(secondaire)* | « Mon parc de logements est-il menacé de dévalorisation ? » | Diagnostic énergétique et climatique du territoire |

## 3. Indicateurs

Chaque indicateur est normalisé de 0 à 100 (rang percentile au sein du même niveau géographique), puis regroupé dans un sous-score.

### Axe A — Potentiel de marché

| Sous-score | Indicateurs | Sources |
|---|---|---|
| **Dynamique** | Évolution du prix au m² (1 et 5 ans), ventes pour 1 000 logements (liquidité) | DVF, INSEE |
| **Demande** | Évolution de la population, emploi, revenu médian, logements autorisés | INSEE, Filosofi, Sitadel |
| **Attractivité** | Équipements, accès à une gare, créations d'entreprises, **sentiment des avis d'habitants** | BPE, SNCF, SIRENE, avis (NLP) |
| **Accessibilité** | Prix d'un logement type rapporté au revenu médian (en années de revenu) | DVF, Filosofi |

### Axe B — Risque de décote à 2040

| Sous-score | Indicateurs | Sources |
|---|---|---|
| **Énergétique** | Part de logements F/G, part de passoires dans les ventes, **décote DPE locale estimée** | DPE ADEME, BDNB, DVF |
| **Climatique actuel** | Arrêtés CatNat, sinistralité, exposition au retrait-gonflement des argiles (carte 2026), zones inondables, recul du trait de côte | Géorisques, ONRN, Cerema |
| **Climatique projeté** | Indicateurs TRACC à +2,7 °C : jours très chauds, sécheresse des sols, pluies extrêmes | DRIAS / Météo-France |

### Indicateurs de synthèse
- `score_potentiel` et `score_risque_2040` (0-100), puis `quadrant`, qui reprend les 4 cases de la matrice.
- **Valeur à risque 2040** (€/m²), calculée selon un **scénario explicite** : prix médian × (part F/G × décote DPE locale + exposition climatique × décote climatique estimée).
  - C'est un **scénario**, pas une prévision : les hypothèses sont affichées dans l'app et peuvent être modifiées.

Les pondérations par profil sont définies dans `config/scoring.yaml` et peuvent être ajustées avec des curseurs dans l'app.

## 4. Place de l'IA

1. **Modèle de prix hédonique** (Spark MLlib), appris sur les ventes DVF enrichies du DPE et des caractéristiques du bâtiment (jointure via la BDNB).
   - Il isole l'effet de la classe DPE et de l'exposition aux risques sur le prix, à caractéristiques égales. On en tire la **valeur verte locale** et la **décote liée aux risques**.
2. **NLP sur du texte** (source textuelle obligatoire) :
   - sentiment et thèmes des avis d'habitants ;
   - mots surveillés : inondation, humidité, chaleur, fissures, bruit ;
   - *(optionnel)* extraction dans les annonces de vente de mentions comme « travaux à prévoir », « isolation refaite » ou « pompe à chaleur ».
3. **Typologie des territoires** (K-Means) pour proposer des « communes comparables ».
4. *(Optionnel)* **Étude d'événement** : évolution des prix avant et après un arrêté CatNat inondation, par la méthode des doubles différences.

Le détail est à documenter dans `docs/05_ia.md`.

## 5. Contraintes du sujet → réponse apportée

| Exigence | Réponse |
|---|---|
| 12 à 50 sources, dont au moins une textuelle | 17 sources principales (voir `02_sources.md`), dont les avis d'habitants ; annonces en option |
| Bases relationnelle ET NoSQL | Lakehouse MinIO + Iceberg, PostgreSQL + PostGIS (couche de service), MongoDB (texte, NLP, JSON brut des API) |
| Indexation et optimisation | Partitionnement Iceberg, index B-tree et GIST, vues matérialisées |
| Standardisation | Code officiel géographique (COG) comme clé pivot, identifiants BAN et parcelle pour les jointures au niveau du bien |
| Spark sur un cluster | Nettoyage, jointure DVF × DPE × BDNB (plusieurs dizaines de millions de lignes), modèle hédonique MLlib |
| App interactive | Carte, matrice potentiel × risque, tableaux exportables, segments de biens, avis |
| Niveaux commune / département / région | Agrégations Spark et dbt |

## 6. Périmètre (projet solo, 1 à 2 mois)
- **Inclus** : **la France entière** (métropole et DROM) : toutes les communes, tous les départements, toutes les régions. On traite les ventes de maisons et d'appartements des 5 dernières années DVF.
- **Trous de couverture connus** (affichés « données non disponibles » dans l'app, jamais à 0) :
  - DVF : Alsace-Moselle (57, 67, 68) et Mayotte ;
  - carte des argiles : métropole uniquement ;
  - DRIAS : projections métropolitaines, avec des jeux de données séparés pour les outre-mer ;
  - Filosofi : petites communes soumises au secret statistique.
- **Méthode** : on développe et on teste sur un échantillon de départements (`DEV_DEPARTEMENTS`), puis **on exécute le pipeline sur la France entière** (`DEV_DEPARTEMENTS` vide). Voir `02b_priorisation_sources.md`.
- **Retiré du cœur** : la dimension locative (loyers, rendement). Le sujet reste centré sur **l'achat et la vente**. La carte des loyers est gardée en option.
- **Bonus visés** :
  - fiche « simulateur de bien » : une adresse → prix estimé, décote DPE, risques (API Géorisques) ;
  - déploiement en ligne ;
  - Superset.

## 7. Planning indicatif (8 semaines)

| Sem. | Objectif | Livrable |
|---|---|---|
| 1 | Infrastructure Docker, référentiel géographique, ingestion DVF | `docker compose up`, tables `ref_*`, DVF dans le bronze |
| 2 | Ingestion : DPE, BDNB, Géorisques, argiles, DRIAS, INSEE | Bronze complet avec manifestes |
| 3 | Silver : nettoyage DVF et DPE, **jointure DVF × DPE via la BDNB** | `silver.dvf_mutations`, `silver.dvf_dpe` |
| 4 | Gold (dbt) : indicateurs, segments, sous-scores ; publication PostgreSQL | Tables `fact_*`, tests dbt |
| 5 | Modèle hédonique (valeur verte, décote risque) et scénario 2040 | `05_ia.md` avec les métriques |
| 6 | Scraping des avis et NLP ; premières pages Streamlit | Collections MongoDB, carte |
| 7 | Matrice de décision, curseurs, segments, export | App complète |
| 8 | Documentation, tests, démo, bonus | Rendu final |

> Chaque semaine correspond à des exercices du [parcours d'apprentissage](06_parcours_apprentissage.md) (E0 à E10).

## 8. Risques projet

| Risque | Parade |
|---|---|
| Jointure DVF × DPE imparfaite (adresses, lots de copropriété) | Passer par la BDNB (parcelle → bâtiment → DPE) ; mesurer et documenter le taux de correspondance |
| Changement de méthode DPE (2021, puis 2026) | Ne garder que les DPE postérieurs à juillet 2021 et ajouter un indicateur « DPE recalculé 2026 » |
| Projections climatiques mal comprises | Afficher le niveau de réchauffement retenu (TRACC) et l'incertitude ; parler de scénario |
| Volumes trop lourds (DPE, BDNB) | Travailler sur quelques départements (`DEV_DEPARTEMENTS`), puis lancer le traitement complet sur le cluster |
