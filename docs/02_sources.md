# Catalogue des sources de données

Toutes les sources sont déclarées dans `config/sources.yaml`, que l'ingestion lit automatiquement.

➡️ **Méthode de sélection, fiches qualifiées, priorités (P0 à P3) et plan de collecte** : voir [`02b_priorisation_sources.md`](02b_priorisation_sources.md).

**Clés de jointure** :
- **au niveau du territoire** : code commune INSEE (COG) ;
- **au niveau du bien** : identifiant de parcelle cadastrale, identifiant de bâtiment BDNB, identifiant d'adresse BAN.

## Sources principales (17)

### Marché immobilier et bâti
| # | Source | Producteur | Format | Maille | Usage |
|---|---|---|---|---|---|
| 1 | [DVF géolocalisées](https://www.data.gouv.fr/datasets/demandes-de-valeurs-foncieres-geolocalisees) | DGFiP / Etalab | CSV.gz annuel | Vente (parcelle + point GPS) | Prix au m², volumes, évolution, liquidité |
| 2 | [DPE logements existants](https://data.ademe.fr/datasets/dpe03existant) ([API](https://www.data.gouv.fr/dataservices/api-dpe-logements)) | ADEME | CSV / API | Logement | Classe énergétique, part de passoires |
| 3 | [BDNB, Base de données nationale des bâtiments](https://www.data.gouv.fr/datasets/base-de-donnees-nationale-des-batiments) ([téléchargement](https://bdnb.io/download/)) | CSTB | CSV / GPKG par département | Bâtiment | **Pont DVF ↔ DPE** (parcelle → bâtiment → DPE), année de construction, matériaux |
| 4 | [Base Adresse Nationale (BAN)](https://adresse.data.gouv.fr/ressources-et-documentations) | IGN / DINUM | CSV / API | Adresse | Géocodage, jointures par adresse (plan B) |
| 5 | [Logements autorisés et commencés (Sitadel)](https://www.data.gouv.fr/datasets/logements-autorises-et-commences-series-mensuelles-communales-en-date-de-prise-en-compte) | SDES | CSV | Commune / mois | Offre neuve, dynamique de construction |

### Risques climatiques
| # | Source | Producteur | Format | Maille | Usage |
|---|---|---|---|---|---|
| 6 | [Géorisques : API et bases GASPAR](https://www.georisques.gouv.fr/donnees/bases-de-donnees) ([doc API](https://www.georisques.gouv.fr/doc-api)) | Ministère de la Transition écologique | API JSON / CSV | Commune / point | Arrêtés CatNat, plans de prévention (PPR), risques recensés |
| 7 | [Exposition au retrait-gonflement des argiles (en vigueur au 01/07/2026)](https://www.data.gouv.fr/datasets/donnees-dexposition-au-retrait-gonflement-des-argiles-en-vigueur-a-partir-du-01-07-2026-1) | BRGM / Géorisques | SHP / GPKG | Zone | Part des bâtiments en exposition forte ou moyenne |
| 8 | [Recul du trait de côte](https://www.data.gouv.fr/datasets/recul-evenementiel-du-trait-de-cote-1) | Cerema / GéoLittoral | SHP | Linéaire côtier | Exposition des communes littorales |
| 9 | [ONRN : indicateurs de sinistralité](https://www.georisques.gouv.fr/articles-risques/onrn/acceder-aux-indicateurs-sinistralite) | ONRN (CCR, France Assureurs, MTE) | CSV | Commune | Coût des sinistres CatNat |
| 10 | [DRIAS : indicateurs par niveau de réchauffement TRACC](https://www.drias-climat.fr/accompagnement/sections/409) | Météo-France | NetCDF / CSV (grille 8 km) | Point de grille → commune | Jours > 35 °C, sécheresse des sols, pluies extrêmes à +2,7 °C |

### Socio-économie et attractivité
| # | Source | Producteur | Format | Maille | Usage |
|---|---|---|---|---|---|
| 11 | [Filosofi 2021](https://www.insee.fr/fr/statistiques/zones/7758831) | INSEE | CSV | Commune | Revenu médian → accessibilité |
| 12 | [Historique des populations communales](https://www.insee.fr/fr/statistiques/3698339) + [dossier complet](https://www.insee.fr/fr/statistiques/5359146) | INSEE | XLSX / CSV | Commune | Démographie, emploi, parc de logements, vacance |
| 13 | [Base permanente des équipements](https://www.insee.fr/fr/statistiques/8217537) | INSEE | CSV / Parquet | Équipement | Attractivité |
| 14 | [Fréquentation en gares](https://www.data.gouv.fr/datasets/frequentation-en-gares) | SNCF | CSV | Gare | Accessibilité ferroviaire |
| 15 | [SIRENE géolocalisée](https://www.data.gouv.fr/datasets/base-sirene-des-etablissements-2024-geolocalisee-geoparquet) | INSEE | GeoParquet | Établissement | Créations d'entreprises (dynamisme économique) |

### Référentiel et texte
| # | Source | Producteur | Format | Maille | Usage |
|---|---|---|---|---|---|
| 16 | [Admin Express COG](https://www.data.gouv.fr/datasets/communes-cantons-et-epci-2025-admin-express-cog-plus-ign) + [API Découpage administratif](https://api.gouv.fr/les-api/api-geo) | IGN / INSEE | GPKG / JSON | Commune → département → région | Référentiel, cartes |
| 17 | **Avis d'habitants** : [ville-ideale.fr](https://www.ville-ideale.fr/), [bien-dans-ma-ville.fr](https://www.bien-dans-ma-ville.fr/) | Sites communautaires | Scraping HTML | Commune | **Source textuelle** : sentiment, thèmes, mentions (inondation, chaleur, humidité…) |

## Sources optionnelles
| Source | Usage |
|---|---|
| Descriptions d'annonces de vente (scraping) | 2ᵉ source textuelle : « travaux à prévoir », « isolation refaite », « pompe à chaleur », « DPE » |
| [Carte des loyers](https://www.data.gouv.fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2025) | Contexte locatif (hors cœur du sujet) |
| [Délinquance enregistrée (SSMSI)](https://www.data.gouv.fr/datasets/bases-statistiques-communale-departementale-et-regionale-de-la-delinquance-enregistree-par-la-police-et-la-gendarmerie-nationales) | Attractivité |
| [Calendrier des interdictions de location DPE (data.gouv)](https://www.data.gouv.fr/datasets/calendrier-interdictions-location-dpe-f-g-e-audit-energetique-2025-2034-bon-cap) | Paramètres du scénario 2040 |

## Références de contexte (citées dans l'app et la soutenance)
- [TRACC, trajectoire de réchauffement de référence](https://www.ecologie.gouv.fr/politiques-publiques/trajectoire-rechauffement-reference-ladaptation-changement-climatique-tracc) : +2 °C en 2030, +2,7 °C en 2050, +4 °C en 2100 ; officielle depuis le 26/01/2026.
- [Notaires de France, étude « valeur verte »](https://www.immobilier.notaires.fr/fr/articles/conseils-et-actualites/actualites/des-transactions-sous-linfluence-de-letiquette-energie) (15/12/2025, données 2024) : maison G environ −25 % et appartement G environ −12 % par rapport à la classe D ; les biens E-F-G représentent environ 40 % des ventes.
- [Réforme du DPE au 01/01/2026](https://www.economie.gouv.fr/actualites/un-nouveau-dpe-au-1er-janvier-2026-pour-favoriser-le-chauffage-electrique) : coefficient de l'électricité ramené de 2,3 à 1,9, environ 850 000 logements sortis du statut de passoire.

## Choix de sourcing
- **Open data public en priorité** : 16 des 17 sources sont officielles.
- **Scraping limité à la source textuelle**, avec :
  - respect du `robots.txt` ;
  - un délai d'au moins 2 s entre deux requêtes ;
  - un User-Agent identifié ;
  - un cache local ;
  - aucune donnée personnelle conservée.
- **Traçabilité** : chaque fichier *bronze* est accompagné d'un `_manifest.json` (URL, date, taille, hash).
