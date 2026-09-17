-- Indicateurs de marché par commune, année et type de bien (+ "Tous")
-- Correspond à la table PostgreSQL fact_marche.

with ventes as (
    select code_insee, annee, type_local, prix_m2, surface_reelle_bati, valeur_fonciere
    from {{ source('silver', 'dvf_mutations') }}
),

par_type as (
    select
        code_insee,
        cast(annee as smallint)                         as annee,
        type_local,
        count(*)                                        as nb_ventes,
        approx_percentile(prix_m2, 0.5)                 as prix_m2_median,
        approx_percentile(prix_m2, 0.25)                as prix_m2_q1,
        approx_percentile(prix_m2, 0.75)                as prix_m2_q3,
        approx_percentile(surface_reelle_bati, 0.5)     as surface_mediane,
        approx_percentile(valeur_fonciere, 0.5)         as valeur_mediane
    from ventes
    group by 1, 2, 3
),

tous_types as (
    select
        code_insee,
        cast(annee as smallint)                         as annee,
        'Tous'                                          as type_local,
        count(*)                                        as nb_ventes,
        approx_percentile(prix_m2, 0.5)                 as prix_m2_median,
        approx_percentile(prix_m2, 0.25)                as prix_m2_q1,
        approx_percentile(prix_m2, 0.75)                as prix_m2_q3,
        approx_percentile(surface_reelle_bati, 0.5)     as surface_mediane,
        approx_percentile(valeur_fonciere, 0.5)         as valeur_mediane
    from ventes
    group by 1, 2
)

select * from par_type
union all
select * from tous_types
