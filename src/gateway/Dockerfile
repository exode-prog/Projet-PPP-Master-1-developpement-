# Dockerfile de la gateway MCP (Sprint 6).
# Meme style que src/target_server/Dockerfile : utilisateur non privilegie,
# dependances mises en cache separement du code applicatif.

FROM python:3.12-slim

WORKDIR /app

# Utilisateur non privilegie - principe de moindre privilege
RUN useradd --no-create-home --shell /usr/sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/gateway/ ./src/gateway/

USER appuser

CMD ["python", "src/gateway/gateway.py"]
