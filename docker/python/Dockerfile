# Image Python partagée : app Streamlit, ingestion, dbt, NLP, API
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libpq-dev git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ENV PYTHONPATH=/opt/homepedia/src
WORKDIR /opt/homepedia
