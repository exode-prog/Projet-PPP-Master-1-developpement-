# Projet de plateforme MCP sécurisée : PPP Master 1

Projet Transversal : Isolation par sandbox, architecture serverless et orchestration cloud.

Ce projet construit une plateforme d'exécution sécurisée pour des serveurs MCP (Model Context Protocol) : un environnement qui permet de faire tourner du code tiers potentiellement non fiable, sans risquer de compromettre la machine hôte, en combinant isolation (sandbox), exécution à la demande (serverless) et un point d'entrée centralisé (gateway).

## Vue d'ensemble

Partie A — Socle commun MCP : un serveur MCP conforme au protocole (Tools, Resources, Prompts), sécurisé par OAuth 2.1 / Keycloak.

Partie B — Spécialité Virtualisation et Cloud :
- Axe 1 : Sandbox et isolation du runtime (gVisor)
- Axe 2 : Architecture serverless et cycle de vie éphémère (k3s, OpenFaaS, LocalStack)
- Axe 3 : Orchestration et gateway d'accès (gateway FastMCP maison)

Démonstration centrale du projet : scénario "attaque contenue" — un serveur MCP volontairement vulnérable est attaqué sans protection (compromission totale), puis avec la plateforme activée (attaque bloquée et contenue). Détail complet : `docs/demo-attaque-contenue.md`.

## Démarrage rapide — Lancer la plateforme

Ces étapes supposent une machine Linux (Ubuntu recommandé) avec Docker déjà installé. Suivre l'ordre : chaque étape dépend de la précédente.

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/exode-prog/Projet-PPP-Master-1-developpement-.git
cd Projet-PPP-Master-1-developpement-
```

### Étape 2 — Vérifier les prérequis système

```bash
docker --version
docker compose version
```

Si absent, installer Docker : https://docs.docker.com/engine/install/ubuntu/

### Étape 3 — Lancer la plateforme principale (axe 3 : gateway + Keycloak)

```bash
docker compose up -d
docker ps   # verifier que keycloak, mcp-gateway, mcp-target-server sont "Up"/"healthy"
```

Le premier démarrage initialise automatiquement le royaume Keycloak (`scripts/keycloak_init.sh`), le client `mcp-target-server` et un utilisateur de test (`testuser`). Keycloak met ~20 secondes à devenir `healthy`.

### Étape 4 — Vérifier que l'authentification fonctionne

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/realms/mcp-secure-platform/protocol/openid-connect/token \
  -d "client_id=mcp-target-server" -d "client_secret=<voir scripts/keycloak_init.sh>" \
  -d "grant_type=password" -d "username=testuser" -d "password=test1234" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -X POST http://127.0.0.1:9000/mcp \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Une réponse `"serverInfo":{"name":"MCP Gateway - Sprint 6"...}` confirme que l'axe 3 fonctionne.

### Étape 5 — Démo sandbox (axe 1 : gVisor vs standard)

**Prérequis** : gVisor (`runsc`) doit être enregistré comme runtime Docker sur la machine (voir https://gvisor.dev/docs/user_guide/install/) — ce n'est pas installé par ce dépôt, c'est un prérequis système.

```bash
docker compose -f docker-compose.vulnerable.yml up -d
docker compose -f docker-compose.vulnerable-hardened.yml up -d
```

Voir `docs/demo-attaque-contenue.md` pour le protocole complet d'exploitation et de comparaison (injection de commande, `CapEff`, écriture/exécution bloquées sous gVisor).

**Ne jamais lancer ces deux composes en dehors d'un réseau isolé ni les fusionner avec `docker-compose.yml`** — voir `src/vulnerable_server/README.md`.

### Étape 6 — Démo serverless (axe 2 : k3s + OpenFaaS)

Nécessite k3s et OpenFaaS installés séparément sur la machine (pas fournis par ce dépôt) :

```bash
curl -sfL https://get.k3s.io | sh -
curl -sLS https://get.arkade.dev | sh
arkade install openfaas
export OPENFAAS_URL=http://127.0.0.1:31112
faas-cli deploy -f stack.yaml
curl -X POST $OPENFAAS_URL/function/mcp-server-function -d '{}'
```

### Étape 7 — Démonstration visuelle (MCP Inspector)

```bash
npx @modelcontextprotocol/inspector
```

Ouvrir l'URL affichée dans un navigateur. Pour tester un serveur protégé par Keycloak, utiliser le champ **Headers** des paramètres de connexion (`Authorization: Bearer <token>`) — ce champ n'est pas sauvegardé entre deux rechargements de page, le ressaisir à chaque session.

### Tout arrêter proprement

```bash
docker compose down
docker compose -f docker-compose.vulnerable.yml down
docker compose -f docker-compose.vulnerable-hardened.yml down
```

## Structure du dépôt

### Documentation technique (`docs/`)

| Document | Contenu |
|---|---|
| `gateway-sprint6.md` | Conteneurisation de la gateway, bugs rencontres et corriges |
| `vulnerabilite-sprint3.md` | La vulnerabilite CWE-78 du serveur cible |
| `comparatif-gvisor-firecracker.md` | Comparaison technologique sandbox |
| `demo-attaque-contenue.md` | Preuve empirique complete du scenario B.2 |
| `no-egress-sprint5.md` | Limitation connue de la NetworkPolicy k3s |
| `integration-3-axes.md` | Comment les 3 axes s'articulent (architecture Option A) |
| `tco.md` | Calcul du cout reel (TCO), sourcé |
| `sprint7-finalisation.md` | Synthese du sprint de finalisation |

## Pour les contributeurs — Configurer son environnement de développement

Chers collègues de EC2LT, suivre ces étapes dans l'ordre pour avoir exactement le même environnement que le reste de l'équipe (dev local, pas nécessaire pour juste lancer la plateforme via Docker ci-dessus).

### 1. Outils système (Ubuntu 24)

```bash
sudo apt update
sudo apt install git python3-venv -y
```

### 2. Environnement Python

```bash
python3 -m venv MCP-PPP
source MCP-PPP/bin/activate
pip install --upgrade pip
pip install fastmcp
```

### 3. Node.js via nvm (nécessaire pour MCP Inspector)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
```

### 4. Ollama et modèle local (optionnel, complément à MCP Inspector)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

### 5. Vérifier que tout fonctionne

```bash
git --version
docker --version
docker compose version
python3 --version
fastmcp --version
node --version
npm --version
ollama --version
```

## Bonnes pratiques de l'équipe

Ne jamais travailler avec le compte root sur la machine de développement. Le projet repose sur le principe de moindre privilège ; travailler avec un utilisateur standard est cohérent avec cette philosophie dès le développement.

Ne jamais committer de token, mot de passe ou secret. Le fichier `.env` est ignoré par Git ; utiliser `.env.example` comme modèle.

## Authentification GitHub

GitHub n'accepte plus les mots de passe classiques en ligne de commande. Chaque membre de l'équipe doit créer son propre token personnel :

1. Aller sur https://github.com/settings/tokens
2. Generate new token, classic
3. Cocher uniquement le scope `repo`
4. Copier le token et l'utiliser comme mot de passe lors du premier `git push`

Pour éviter de ressaisir le token à chaque fois :

```bash
git config --global credential.helper store
```

## Document de référence

En cas de blocage, j'ai partagé mon fichier docx ici, ça peut vous aider :
https://docs.google.com/document/d/1XvrIbPh8w_J7UX1EusB-1BuBKecIPWpmOzRJd9BoSaU/edit?usp=sharing

## Roadmap (les sprints)

Voir le détail complet des tâches dans `docs/PPP_Planning_Sprints.docx` et le tracker `docs/PPP_Sprints_Taches.xlsx`.

- Sprint 0 : Setup et cadrage
- Sprint 1 : Socle commun MCP
- Sprint 2 : Sécurité applicative (Keycloak, OAuth 2.1, RBAC)
- Sprint 3 : Serveur MCP vulnérable (cobaye pour la démo)
- Sprint 4 : Sandbox et isolation runtime (gVisor)
- Sprint 5 : Serverless et cycle de vie éphémère
- Sprint 6 : Orchestration et gateway
- Sprint 7 : Intégration finale, TCO et livrables

## Contribution de l'équipe

1. Créer une branche à partir de `main` : `git checkout -b feature/nom-de-la-tache`
2. Committer avec des messages clairs : `git commit -m "Sprint 1 : ajout du Tool add()"`
3. Pousser et ouvrir une Pull Request : `git push origin feature/nom-de-la-tache`
4. Demander une revue à au moins un coéquipier avant de fusionner

## Sécurité

Ce dépôt contient volontairement, à partir du Sprint 3, un serveur MCP vulnérable utilisé à des fins pédagogiques et démonstratives. Ne jamais déployer ce code en dehors d'un environnement de laboratoire isolé. Voir `src/vulnerable_server/README.md` pour les règles d'isolation strictes.

## Licence

Projet académique, usage pédagogique uniquement.
