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

## Démarrage rapide — reproduire exactement le même environnement

Ces étapes partent d'une machine Linux (Ubuntu recommandé) **sans aucun prérequis déjà installé**. Chaque étape donne la commande d'installation si l'outil est absent, puis la commande de vérification. Suivre l'ordre : chaque étape dépend de la précédente.

Chaque test est marqué **[CLI]** (ligne de commande, terminal) ou **[GUI]** (interface graphique, navigateur) — certains ont les deux.

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/exode-prog/Projet-PPP-Master-1-developpement-.git
cd Projet-PPP-Master-1-developpement-
```

### Étape 2 — Installer Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # ou se déconnecter/reconnecter pour appliquer le groupe
docker --version
docker compose version
```

### Étape 3 — Installer Node.js via nvm (nécessaire pour MCP Inspector, tests [GUI])

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
node --version
npm --version
```

### Étape 4 — Lancer la plateforme principale (axe 3 : gateway + Keycloak)

```bash
docker compose up -d
docker ps   # vérifier que keycloak, mcp-gateway, mcp-target-server sont "Up"/"healthy"
```

Le premier démarrage initialise automatiquement le royaume Keycloak (`scripts/keycloak_init.sh`), le client `mcp-target-server` et un utilisateur de test (`testuser`). Keycloak met ~20 secondes à devenir `healthy`.

### Étape 5 — Tester l'authentification : axe 3 **[CLI obligatoire + GUI optionnel]**

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

Une réponse `"serverInfo":{"name":"MCP Gateway - Sprint 6"...}` confirme que l'axe 3 fonctionne. **Ce test CLI est la preuve retenue et documentée**, car reproductible et scriptable.

Un test **[GUI]** complémentaire est possible, mais seulement comme démonstration ponctuelle : juste après avoir obtenu `$TOKEN` ci-dessus, le coller dans le champ **Headers** de MCP Inspector (`Authorization: Bearer <valeur de $TOKEN>`) avant de se connecter à `http://127.0.0.1:9000/mcp`. Ce champ n'étant pas sauvegardé entre deux rechargements de page, il faut ressaisir le jeton à chaque session — ce qui le rend impropre comme preuve documentée, mais utilisable pour une démo live.

### Étape 6 — Installer gVisor (prérequis axe 1)

```bash
(
  set -e
  ARCH=$(uname -m)
  URL=https://storage.googleapis.com/gvisor/releases/release/latest/${ARCH}
  wget ${URL}/runsc ${URL}/runsc.sha512 \
    ${URL}/containerd-shim-runsc-v1 ${URL}/containerd-shim-runsc-v1.sha512
  sha512sum -c runsc.sha512 -c containerd-shim-runsc-v1.sha512
  rm -f *.sha512
  chmod a+rx runsc containerd-shim-runsc-v1
  sudo mv runsc containerd-shim-runsc-v1 /usr/local/bin
)
sudo runsc install   # enregistre automatiquement le runtime "runsc" dans Docker
sudo systemctl restart docker
docker info | grep -A2 Runtimes   # doit lister "runsc"
```

Source officielle : https://gvisor.dev/docs/user_guide/install/

### Étape 7 — Démo sandbox : axe 1, standard vs gVisor **[CLI + GUI]**

```bash
docker compose -f docker-compose.vulnerable.yml up -d
docker compose -f docker-compose.vulnerable-hardened.yml up -d
```

**Ne jamais lancer ces deux composes en dehors d'un réseau isolé ni les fusionner avec `docker-compose.yml`** — voir `src/vulnerable_server/README.md`.

- **[GUI]** Démo via MCP Inspector (voir étape 10 pour le lancement) : exploiter l'injection de commande sur l'outil `ping_host`, comparer serveur sans protection (port 8001) vs serveur durci (port 8002). Payload de test : `127.0.0.1; whoami; id` (compromission) ou `127.0.0.1; cat /proc/version` (preuve d'exposition noyau).
- **[CLI]** Vérification complémentaire des capacités effectives et de l'exposition noyau :
```bash
  docker exec mcp-vulnerable-server-UNSAFE sh -c "cat /proc/1/status | grep CapEff"
  docker exec mcp-vulnerable-server-HARDENED sh -c "cat /proc/1/status | grep CapEff"
  docker exec mcp-vulnerable-server-UNSAFE sh -c "cat /proc/version"
  docker exec mcp-vulnerable-server-HARDENED sh -c "cat /proc/version"
```

Protocole complet et résultats de référence : `docs/demo-attaque-contenue.md`.

### Étape 8 — Installer k3s et OpenFaaS (prérequis axe 2)

```bash
curl -sfL https://get.k3s.io | sh -
curl -sLS https://get.arkade.dev | sh
arkade install openfaas
```

### Étape 9 — Démo serverless : axe 2 **[CLI + GUI]**

- **[CLI]** (preuve retenue et documentée, testée et confirmée) :
```bash
  export OPENFAAS_URL=http://127.0.0.1:31112
  faas-cli deploy -f stack.yaml
  curl -X POST $OPENFAAS_URL/function/mcp-server-function -d '{}'
```

- **[GUI]** (testé et confirmé le 2026-10-04) : OpenFaaS fournit un portail web accessible sur l'URL du gateway, permettant de voir les fonctions déployées et de les invoquer avec un payload texte, derrière une authentification basique :
```bash
  PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode)
  echo "Utilisateur: admin / Mot de passe: $PASSWORD"
  # Ouvrir http://127.0.0.1:31112/ui/ dans un navigateur et se connecter avec ces identifiants
```
  La fonction `mcp-server-function` apparaît dans la liste ; cliquer dessus permet de l'invoquer directement depuis l'interface (bouton "Invoke").

### Étape 9bis — Démo complémentaire : cycle éphémère automatique via LocalStack **[CLI]**

Contrairement à OpenFaaS (scale manuel), LocalStack émule le runtime AWS Lambda officiel et démontre un cycle de vie réellement automatique (création à l'invocation, destruction après inactivité, sans intervention). Détail et limite d'OpenFaaS à ce sujet : `docs/axe2-scale-to-zero.md`.

```bash
docker compose -f docker-compose.localstack.yml up -d
sleep 10

awslocal lambda create-function \
  --function-name mcp-lambda-function \
  --runtime python3.12 --handler handler.handler \
  --zip-file fileb://localstack-lambda/function.zip \
  --role arn:aws:iam::000000000000:role/lambda-role

# Attendre l'état Active avant d'invoquer (la fonction reste "Pending" quelques secondes)
for i in {1..15}; do
  STATE=$(awslocal lambda get-function --function-name mcp-lambda-function --query 'Configuration.State' --output text)
  [ "$STATE" = "Active" ] && break
  sleep 2
done

docker ps   # avant : seuls localstack-mcp et local-registry
awslocal lambda invoke --function-name mcp-lambda-function output.json
cat output.json
docker ps   # après : un conteneur public.ecr.aws/lambda/python:3.12 est apparu

# Laisser tourner sans ré-invoquer pour observer la disparition automatique (~20 min)
watch -n 5 docker ps
```

### Étape 10 — Démonstration visuelle **[GUI]** (MCP Inspector)

```bash
npx @modelcontextprotocol/inspector
```

Ouvrir l'URL affichée dans un navigateur, se connecter en Streamable HTTP sur `http://127.0.0.1:8001/mcp` (sans protection) ou `http://127.0.0.1:8002/mcp` (durci gVisor) pour la démo de l'axe 1. Pour l'axe 3, voir la note GUI optionnelle de l'étape 5.

### Étape 11 (optionnelle) — Ollama comme hôte MCP autonome

Complément à MCP Inspector (A.5 du cahier des charges) : un LLM local exécute les appels d'outils à la place d'un humain. Non requis pour valider la plateforme.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
python3 -m venv MCP-PPP
source MCP-PPP/bin/activate
pip install mcp-client-for-ollama
ollmcp -u http://127.0.0.1:8001/mcp -m qwen2.5:3b
```

Une fois connecté, ollmcp ouvre une invite interactive. Taper la question suivante (en langage naturel, c'est le modèle qui construit lui-même l'appel à l'outil `ping_host`) :
Peux-tu vérifier si l'hôte 127.0.0.1; whoami; id est joignable ?

Avant d'exécuter quoi que ce soit, ollmcp affiche l'appel d'outil que le modèle a construit et demande une confirmation humaine (HIL — Human-In-the-Loop) :
Tool call: ping_host
Arguments: {"hostname": "127.0.0.1; whoami; id"}
Allow this tool call? [y/n]

Répondre `y` pour autoriser l'exécution (ou `n` pour l'annuler — c'est ce blocage qui matérialise le "consentement explicite de l'utilisateur" exigé par le cahier des charges, partie A.6). Une fois confirmé, la réponse de l'outil s'affiche :
root
uid=0(root) gid=0(root) groups=0(root)

Ceci confirme deux choses à la fois : que le modèle a transmis la commande d'injection sans la filtrer (il suit l'instruction de l'utilisateur telle quelle), et que la validation humaine (HIL) intervient bien avant toute exécution réelle — sans ce `y`, la commande n'aurait pas été lancée.

Détail et transcript de référence : `docs/demo-ollama.md`.

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
| `demo-ollama.md` | Démonstration Ollama/ollmcp comme hôte MCP autonome |
| `no-egress-sprint5.md` | Limitation connue de la NetworkPolicy k3s |
| `integration-3-axes.md` | Comment les 3 axes s'articulent (architecture Option A) |
| `axe2-scale-to-zero.md` | Investigation scale-to-zero (OpenFaaS vs Knative vs LocalStack), causes racines |
| `tco.md` | Calcul du cout reel (TCO), sourcé |
| `sprint7-finalisation.md` | Synthese du sprint de finalisation |

## Pour les contributeurs — Configurer son environnement de développement

Chers collègues de EC2LT : Docker, Node.js et gVisor sont couverts dans "Démarrage rapide" ci-dessus. Les étapes suivantes ne concernent que le développement du code Python du projet (pas nécessaire pour juste lancer et tester la plateforme).

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

### 3. Vérifier que tout fonctionne

```bash
git --version
docker --version
docker compose version
python3 --version
fastmcp --version
node --version
npm --version
ollama --version   # si installé (étape 11, optionnelle)
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

## Difficultés et limites rencontrées

Par souci de transparence (et conformément à la méthodologie du projet : vérifier avant de conclure), voici les principales difficultés rencontrées et comment elles ont été traitées — aucune n'a été contournée en silence.

| Difficulté | Constat | Traitement |
|---|---|---|
| Scale-to-zero OpenFaaS indisponible | Fonctionnalité réservée à l'édition Pro, confirmé par la doc officielle et reconfirmé empiriquement (déploiement actif sans interruption sur plusieurs jours) | Cycle de vie manuel retenu (`spawn.sh`/`teardown.sh`) ; preuve du concept via LocalStack à la place. Détail : `docs/axe2-scale-to-zero.md` |
| Knative comme alternative à OpenFaaS | Bug DNS chronique et bloquant (`activator` → `autoscaler`), 28 échecs reproductibles sur 144 minutes, 4 hypothèses testées et éliminées | Piste abandonnée et documentée avec sa cause racine plutôt que masquée. Détail : `docs/axe2-scale-to-zero.md` |
| NetworkPolicy no-egress (axe 2) | Définie (`no-egress-policy.yaml`) mais non appliquée en pratique : le CNI Flannel par défaut de k3s ne supporte pas les NetworkPolicy | Limitation assumée et documentée (`docs/no-egress-sprint5.md`) ; isolation réseau du projet reposant sur la séparation des réseaux Docker de l'axe 1 |
| Interruption silencieuse de Keycloak | Conteneur trouvé `Exited (255)` sans trace d'erreur applicative, probablement liée à un redémarrage VM/Docker externe au projet | Diagnostiqué par élimination (`docker inspect`, logs horodatés) plutôt que supposé être un bug de code ; relancé et revalidé de bout en bout |
| Variabilité de mesure du cold-start gVisor | Trois mesures indépendantes ont donné des écarts importants (6,8 % à 120 % de surcoût CPU) selon le délai avant mesure | Présenté honnêtement comme une plage et non un chiffre unique, avec la cause probable documentée (`docs/tco.md`) plutôt qu'un chiffre choisi arbitrairement |
| Champ Headers non persistant dans MCP Inspector | Le champ existe bien (recherché et confirmé, contrairement à une hypothèse initiale erronée) mais sa valeur n'est pas sauvegardée entre rechargements de page | Authentification documentée comme test CLI obligatoire (`curl`) ; GUI utilisable seulement en démonstration ponctuelle |
| Proxy serverless incomplet | Le handler OpenFaaS renvoie une confirmation statique plutôt que de relayer une vraie session MCP, alors que son docstring initial le suggérait | Docstring corrigé pour rester fidèle au code ; portée du test clarifiée comme preuve de concept du mécanisme serverless, pas une intégration fonctionnelle axe 1/2/3 |

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
