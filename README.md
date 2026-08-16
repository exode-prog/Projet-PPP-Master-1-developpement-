# Projet de plateforme MCP sécurisée : PPP Master 1

Projet Transversal : Isolation par sandbox, architecture serverless et orchestration cloud.

Ce projet construit une plateforme d'exécution sécurisée pour des serveurs MCP (Model Context Protocol) : un environnement qui permet de faire tourner du code tiers potentiellement non fiable, sans risquer de compromettre la machine hôte, en combinant isolation (sandbox), exécution à la demande (serverless) et un point d'entrée centralisé (gateway).

## Vue d'ensemble

Partie A — Socle commun MCP : un serveur MCP conforme au protocole (Tools, Resources, Prompts), sécurisé par OAuth 2.1 / Keycloak.

Partie B — Spécialité Virtualisation et Cloud :
- Axe 1 : Sandbox et isolation du runtime (gVisor, seccomp, AppArmor)
- Axe 2 : Architecture serverless et cycle de vie éphémère (k3s, LocalStack)
- Axe 3 : Orchestration et gateway d'accès (Docker MCP Gateway)

Démonstration centrale du projet : scénario "attaque contenue" — un serveur MCP volontairement vulnérable est attaqué sans protection (compromission totale), puis avec la plateforme activée (attaque bloquée et contenue).

## Structure du dépôt

```
mcp-secure-platform/
├── src/target_server/       serveur MCP de démo, puis serveur cible vulnérable
├── sandbox/                 profils gVisor, seccomp, AppArmor
├── serverless/               manifests k3s, config LocalStack, scripts spawn/teardown
├── gateway/                  config Docker MCP Gateway ou proxy FastMCP
├── docs/                     rapport, schémas, cahier des charges technique
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Installation — Rejoindre le projet (pour l'équipe)

Chers collègues de EC2LT, merci de suivre ces étapes dans l'ordre pour avoir exactement le même environnement que le reste de l'équipe. Le détail des versions exactes validées est dans `docs/cahier-des-charges-technique.md`.

### 1. Cloner le dépôt

```bash
git clone https://github.com/exode-prog/Projet-PPP-Master-1-developpement-.git
cd Projet-PPP-Master-1-developpement-
```

### 2. Outils système (Ubuntu 24)

```bash
sudo apt update
sudo apt install git python3-venv -y
```

Pour Docker, suivre la documentation officielle : https://docs.docker.com/engine/install/ubuntu/

### 3. Environnement Python

```bash
python3 -m venv MCP-PPP
source MCP-PPP/bin/activate
pip install --upgrade pip
pip install fastmcp
```

### 4. Node.js via nvm (nécessaire pour MCP Inspector)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
```

### 5. Ollama et modèle local

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
```

### 6. Vérifier que tout fonctionne

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

Toutes les commandes doivent répondre sans erreur. En cas de doute sur une version, vérifier dans `docs/cahier-des-charges-technique.md`.

### 7. Lancer MCP Inspector (outil de débogage)

```bash
npx @modelcontextprotocol/inspector
```

Ouvrir ensuite l'URL affichée dans le terminal dans un navigateur.

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

En cas de blocage,  j ai partage mon fichier docx ici ca peut  vous aider :
https://docs.google.com/document/d/1XvrIbPh8w_J7UX1EusB-1BuBKecIPWpmOzRJd9BoSaU/edit?usp=sharing

## Roadmap (les  sprints)

Voir le détail complet des tâches dans `docs/PPP_Planning_Sprints.docx` et le tracker `docs/PPP_Sprints_Taches.xlsx`.

- Sprint 0 : Setup et cadrage
- Sprint 1 : Socle commun MCP
- Sprint 2 : Sécurité applicative (Keycloak, OAuth 2.1, RBAC)
- Sprint 3 : Serveur MCP vulnérable (cobaye pour la démo)
- Sprint 4 : Sandbox et isolation runtime (gVisor)
- Sprint 5 : Serverless et cycle de vie éphémère
- Sprint 6 : Orchestration et gateway
- Sprint 7 : Intégration finale, démo et livrables

## Contribution de l'équipe

1. Créer une branche à partir de `main` : `git checkout -b feature/nom-de-la-tache`
2. Committer avec des messages clairs : `git commit -m "Sprint 1 : ajout du Tool add()"`
3. Pousser et ouvrir une Pull Request : `git push origin feature/nom-de-la-tache`
4. Demander une revue à au moins un coéquipier avant de fusionner

## Sécurité

Ce dépôt contient volontairement, à partir du Sprint 3, un serveur MCP vulnérable utilisé à des fins pédagogiques et démonstratives. Ne jamais déployer ce code en dehors d'un environnement de laboratoire isolé.

## Licence

Projet académique, usage pédagogique uniquement.
