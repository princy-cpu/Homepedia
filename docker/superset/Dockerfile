# Bonus BI : Superset connecté à Trino (et PostgreSQL)
FROM apache/superset:4.1.2

USER root
RUN pip install --no-cache-dir "trino[sqlalchemy]==0.330.0" psycopg2-binary==2.9.10
USER superset

# Initialisation au premier démarrage, puis lancement du serveur
CMD ["/bin/sh", "-c", "superset db upgrade && \
  superset fab create-admin --username admin --firstname Admin --lastname Homepedia --email admin@homepedia.local --password \"$ADMIN_PASSWORD\" || true; \
  superset init && \
  gunicorn --bind 0.0.0.0:8088 --workers 2 --timeout 120 'superset.app:create_app()'"]

# Connexion à ajouter dans l'UI Superset :
#   trino://admin@trino:8080/iceberg
