FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .

RUN pip install --no-cache-dir -r requirements-docker.txt

COPY ingestion ./ingestion
COPY experimentation ./experimentation
COPY forecasting ./forecasting
COPY docs/forecasting ./docs/forecasting
COPY ai ./ai
COPY orchestration ./orchestration
COPY analytics ./analytics
COPY dashboard/data/ab_testing ./dashboard/data/ab_testing
COPY ["dashboard/Data Analytics.SemanticModel/definition", "dashboard/Data Analytics.SemanticModel/definition"]
COPY tests ./tests

CMD ["python", "-m", "pytest", "-v"]
