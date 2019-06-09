FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
MAINTAINER "nathan@code.databio.org"

# TODO: Replace with pypi when refgenconf and yacman are stable
# RUN pip install refgenconf
RUN pip install yacman
RUN pip install https://github.com/databio/refgenconf/archive/master.zip

# This adds in some dummy demo files to be served in tested.
# In production, you should mount your refgenie server genomes in /genomes
COPY files /genomes

COPY . /app
RUN pip install -r /app/requirements/requirements-all.txt
RUN pip install .
