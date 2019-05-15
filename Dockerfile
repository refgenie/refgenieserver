FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
MAINTAINER "nathan@code.databio.org"

RUN pip install fastapi
RUN pip install aiofiles # used by starlette for StaticFiles
RUN pip install jinja2

# TODO: Replace with pypi when refgenconf is stable
# RUN pip install refgenconf
RUN pip install https://github.com/databio/yacman/archive/master.zip
RUN pip install https://github.com/databio/refgenconf/archive/master.zip

# This adds in some dummy demo files to be served in tested.
# In production, you should mount your refgenie server genomes in /genomes
COPY files /genomes


COPY . /app
# RUN pip install -r /app/requirements.txt
