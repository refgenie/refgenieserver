FROM python:3.12-slim
LABEL authors="Nathan Sheffield, Michal Stolarczyk"

COPY . /app
WORKDIR /app
RUN pip install .
CMD ["uvicorn", "refgenieserver.main:app", "--host", "0.0.0.0", "--port", "80"]
