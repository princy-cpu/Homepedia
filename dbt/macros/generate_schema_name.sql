{# Utiliser le schéma tel quel (gold) au lieu de "<target>_gold" #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name is not none else target.schema }}
{%- endmacro %}
