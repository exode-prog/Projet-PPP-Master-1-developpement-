# Cahier des charges technique du Sprint 0

Projet : Plateforme MCP sécurisée : PPP Master 1
Environnement de référence : Une machine virtuelle Ubuntu 24, 

Ce document fige les versions exactes des outils validés lors du Sprint 0. Toute personne rejoignant le projet doit installer ces mêmes versions, ou des versions compatibles, pour garantir un environnement homogène entre l'équipe.

## Stack validée

| Outil | Version validée | Rôle dans le projet |
|---|---|---|
| OS | Ubuntu 24 | Système hôte de développement |
| Git | 2.43.0 | Versionning et collaboration |
| Docker | 29.7.2 | Conteneurisation de base |
| Docker Compose | v5.4.0 | Orchestration multi-conteneurs locale |
| Python | 3.12.3 | Langage principal des serveurs MCP |
| FastMCP | 3.4.7 | Framework de développement MCP |
| Ollama | 0.32.13 | Runtime LLM local |
| Modèle LLM | qwen2.5:3b | Modèle de test pour la démo |
| Node.js | 22.23.2 LTS | Runtime pour MCP Inspector |
| npm | 10.9.8 | Gestionnaire de paquets Node |
| MCP Inspector | 2.2.0 | Outil de debug et de test MCP |

## Choix techniques justifiés

Utilisateur non-root : le développement se fait avec un utilisateur standard, jamais root, cohérent avec le principe de moindre privilège appliqué dans l'ensemble du projet.

Environnement virtuel Python (venv) : isolation des dépendances Python du système, nom de convention MCP-PPP pour toute l'équipe.

nvm pour Node.js : plutôt que le paquet apt, souvent obsolète, pour garantir une version récente et contrôlable, Node 22 LTS.

Authentification GitHub par token personnel : le mot de passe classique est désactivé côté GitHub depuis 2021. Le token permet un accès révocable et limité au scope repo uniquement.

Modèle LLM léger qwen2.5:3b : choisi pour rester compatible avec une VM à 4-8 Go de RAM, tout en supportant les appels d'outils nécessaires aux tests MCP.

## Procédure de reproduction de l'environnement

Outils système :
