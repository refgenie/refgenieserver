FROM tiangolo/uvicorn-gunicorn:python3.8-alpine3.10
LABEL authors="Nathan Sheffield, Michal Stolarczyk"

COPY . /app
RUN apk add --no-cache --virtual .build-deps postgresql-dev gcc python3-dev musl-dev bash git openssh
RUN git clone https://github.com/vishnubob/wait-for-it.git
RUN pip install .