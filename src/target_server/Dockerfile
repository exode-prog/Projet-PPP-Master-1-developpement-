# Dockerfile du serveur MCP "cible" (Sprint 1 — version de base).
# Sera durci progressivement à partir du Sprint 4 (gVisor, seccomp, AppArmor).

FROM python:3.12-slim

WORKDIR /app

# Création d'un utilisateur non privilégié — principe de moindre privilège
RUN useradd --no-create-home --shell /usr/sbin/nologin appuser

# Installation des dépendances (mise en cache Docker optimisée)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code du serveur
COPY src/target_server/ ./src/target_server/

# Le dossier de travail appartient a root apres les etapes precedentes (WORKDIR,
# COPY). On le confie a appuser avant de basculer dessus, pour que le serveur
# puisse ecrire son journal d'audit (audit.log, chemin relatif a /app).
RUN chown -R appuser:appuser /app

# Bascule vers l'utilisateur non privilégié pour l'exécution
USER appuser

CMD ["python", "src/target_server/server.py"]
