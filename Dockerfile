# Linux test image for ai-tts portable core
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements-dev.txt pyproject.toml ./
COPY src ./src
COPY tests ./tests
COPY docs ./docs
COPY README.md LICENSE install.sh config.example.json pytest.ini ./

RUN pip install --no-cache-dir -r requirements-dev.txt \
    && pip install --no-cache-dir -e .

# Default: unit tests only (no live API)
ENV PYTHONUNBUFFERED=1
CMD ["pytest", "-q", "--ignore=tests/test_live_optional.py"]
