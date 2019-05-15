FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
MAINTAINER "nathan@code.databio.org"

RUN pip install fastapi
RUN pip install aiofiles # used by starlette for StaticFiles
RUN pip install jinja2

# TODO: Replace with pypi when refgenconf is stable
RUN pip install https://github.com/databio/refgenconf/archive/master.zip
RUN pip install https://github.com/databio/yacman/archive/master.zip


COPY files /genomes
COPY . /app
# RUN pip install -r /app/requirements.txt
