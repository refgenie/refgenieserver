FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
LABEL authors="Nathan Sheffield, Michal Stolarczyk"

COPY . /app
RUN apk update
RUN apk add make automake gcc g++ subversion python3-dev
RUN pip install https://github.com/databio/yacman/archive/dev.zip
RUN pip install https://github.com/refgenie/refgenconf/archive/dev.zip
RUN pip install https://github.com/databio/henge/archive/master.zip
RUN pip install https://github.com/refgenie/seqcol/archive/master.zip
RUN pip install .