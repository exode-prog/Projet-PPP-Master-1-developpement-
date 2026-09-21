# Dockerfile du serveur MCP VULNÉRABLE (Sprint 3).
# Usage strictement limité au laboratoire de démonstration.

FROM python:3.12-slim

# Nécessaire pour que le Tool ping_host fonctionne (la commande ping)
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/vulnerable_server/ ./src/vulnerable_server/

# Note : contrairement au serveur principal, PAS d'utilisateur non-root ici
# intentionnellement, pour le Sprint 3 (baseline "sans protection").
# Le Sprint 4 comparera avec une version durcie.

CMD ["python", "src/vulnerable_server/server.py"]
