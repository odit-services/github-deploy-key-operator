FROM python:3.11-slim

LABEL org.opencontainers.image.source=https://github.com/gurghet/github-deploy-key-operator

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Create non-root user and set up home directory
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER 1000

COPY operator.py .

CMD ["kopf", "run", "--standalone", "operator.py"]
