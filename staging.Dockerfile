FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
LABEL authors="Nathan Sheffield, Michal Stolarczyk"

COPY . /app
RUN pip install .
