FROM tiangolo/uvicorn-gunicorn:python3.8-alpine3.10
LABEL authors="Nathan Sheffield, Michal Stolarczyk"

COPY . /app
RUN pip install https://github.com/pepkit/ubiquerg/archive/dev.zip
RUN pip install https://github.com/refgenie/refgenconf/archive/dev.zip
RUN pip install .
