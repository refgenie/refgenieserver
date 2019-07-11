FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
MAINTAINER "nathan@code.databio.org"

# This adds in some dummy demo files to be served in tested.
# In production, you should mount your refgenie server genomes in /genomes
COPY files /genomes

COPY . /app

RUN pip install .
