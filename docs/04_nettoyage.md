# Méthodologie de nettoyage des données

> Document exigé par le sujet. Complète chaque section au fur et à mesure que les jobs sont écrits.
> Pour chaque règle, note le **nombre de lignes avant et après** : le jury apprécie les chiffres.

## Règles transverses (toutes sources)

| Règle | Détail |
|---|---|
| Code commune | Converti en texte sur 5 caractères, avec les zéros initiaux (`1004` → `01004`). Corse en `2A` / `2B`. |
| Arrondissements PLM | Paris (751xx), Lyon (6938x) et Marseille (132xx) sont ramenés à la commune (75056, 69123, 13055) pour les agrégats communaux. Le détail par arrondissement est conservé dans silver. |
| Communes fusionnées | La table de passage COG (INSEE) ramène les anciens codes vers le code en vigueur. |
| Types | Dates au format ISO, montants en `decimal`, suppression des espaces insécables, virgule décimale convertie en point. |
| Doublons | Dédoublonnage sur la clé métier propre à chaque source. |
| Traçabilité | Colonnes `_source`, `_ingested_at` et `_bronze_path` ajoutées dans silver. |

## DVF (`silver.dvf_mutations`)

1. Ne conserver que `nature_mutation = 'Vente'`.
2. Ne conserver que `type_local ∈ {Maison, Appartement}`.
3. **Mutations multi-lignes** : dans DVF, une vente peut apparaître sur plusieurs lignes (plusieurs lots ou parcelles), avec la même valeur foncière répétée.
   - Regrouper par `id_mutation`.
   - Exclure les mutations qui portent sur plusieurs logements, car leur prix au m² n'est pas calculable.
4. Écarter les lignes sans surface ou avec une `surface_reelle_bati` inférieure à 9 m².
5. Calculer `prix_m2 = valeur_fonciere / surface_reelle_bati`.
6. **Valeurs aberrantes** : exclure les prix au m² hors de [Q1 − 1,5 × IQR ; Q3 + 1,5 × IQR], calculés par département et par type de bien. Ajouter en plus des bornes absolues (entre 300 et 30 000 €/m²).
7. Partitionner la table par `annee` et `code_departement`.

| Étape | Lignes restantes |
|---|---|
| Brut (5 ans) | à compléter |
| Après filtre Vente + type | à compléter |
| Après dédoublonnage des mutations | à compléter |
| Après suppression des valeurs aberrantes | à compléter |

## DPE (ADEME)
- Ne garder que les DPE établis **depuis juillet 2021** (nouvelle méthode, opposable).
- Garder le DPE **le plus récent** par logement (identifiant BAN + étage / complément d'adresse).
- **Réforme 2026** : pour les logements chauffés à l'électricité, ajouter l'indicateur `dpe_recalcule_2026`.
  - Il vaut `vrai` pour les DPE établis à partir du 01/01/2026.
  - Pour les DPE plus anciens, le calcul utilisait encore le coefficient 2,3. Leur classe est signalée comme « potentiellement surestimée », au lieu d'être recalculée à la main.
- Calculer par commune : `part_dpe_fg`, `part_dpe_e` et la répartition des logements par classe.

## Jointure DVF × DPE (`silver.dvf_dpe`)
1. **Voie principale, via la BDNB** : parcelle DVF (`id_parcelle`) → bâtiments de la parcelle (`rel_batiment_groupe_parcelle`) → DPE représentatif du bâtiment.
   - Pour une **maison**, on retient le DPE du bâtiment.
   - Pour un **appartement**, le DPE du bâtiment n'est qu'une approximation. On le signale avec `dpe_niveau = 'batiment'`.
2. **Voie secondaire, par adresse** : adresse DVF normalisée ou coordonnées → identifiant BAN → DPE du logement, en ne gardant que le DPE le plus proche de la date de vente.
3. **Règles** :
   - ne jamais utiliser un DPE établi plus de 2 ans **après** la vente, car il pourrait refléter des travaux faits après l'achat ;
   - conserver le mode de correspondance dans la colonne `match_type` (`bdnb`, `ban`, `aucun`).
4. **Taux de correspondance** à publier, par département et par type de bien :

| Département | Ventes | Avec DPE | Taux |
|---|---|---|---|
| à compléter | | | |

> ⚠️ Les noms exacts des tables et colonnes de la BDNB sont à vérifier dans le dictionnaire de données du millésime téléchargé.

## Risques climatiques
- **Argiles (carte 2026)** : intersection spatiale entre les zones d'exposition et les bâtiments (BDNB). On en tire, par commune, la part de bâtiments en exposition forte ou moyenne.
- **CatNat (GASPAR)** : nombre d'arrêtés sur 10 ans par commune, par type de péril ; dédoublonnage par numéro d'arrêté.
- **DRIAS** : chaque point de la grille de 8 km est rattaché à la commune qui contient son centroïde (ou au point le plus proche). On garde le niveau de réchauffement TRACC retenu (+2,7 °C).
- **Trait de côte** : distance du centroïde de la commune au linéaire en recul ; drapeau `commune_littorale_exposee`.

## SIRENE
- Ne garder que les établissements **actifs** (`etatAdministratifEtablissement = 'A'`).
- Créations d'établissements sur les 3 dernières années, rapportées à la population.

## Avis d'habitants (MongoDB)
- Retirer les balises HTML, normaliser les espaces et l'Unicode (NFC).
- Détecter la langue et ne garder que le français.
- Supprimer les doublons exacts (hash du texte).
- Supprimer les pseudonymes (aucune donnée personnelle conservée).

## Contrôles qualité (tests dbt)
- `not_null` et `unique` sur les clés.
- `relationships` : chaque `code_insee` existe dans `ref_commune`.
- Bornes : prix au m² et rendement dans des intervalles plausibles.
