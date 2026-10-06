# Projet de plateforme MCP sécurisée : PPP Master 1

Projet Transversal : Isolation par sandbox, architecture serverless et orchestration cloud.

Plateforme d'exécution sécurisée pour serveurs MCP (Model Context Protocol) : exécuter du code tiers non fiable sans compromettre l'hôte, via sandbox, exécution à la demande (serverless) et point d'entrée centralisé (gateway).

## Vue d'ensemble

**Partie A : Socle commun MCP** : serveur MCP conforme au protocole (Tools, Resources, Prompts), sécurisé par OAuth 2.1 / Keycloak.

**Partie B : Virtualisation et Cloud** :
- Axe 1 : Sandbox et isolation du runtime (gVisor)
- Axe 2 : Architecture serverless et cycle de vie éphémère (k3s, OpenFaaS, LocalStack)
- Axe 3 : Orchestration et gateway d'accès (gateway FastMCP maison)

**Démo centrale** : "attaque contenue"  serveur MCP vulnérable attaqué sans protection (compromission totale) puis avec la plateforme (attaque bloquée/contenue). Détail : `docs/demo-attaque-contenue.md`.

## Démarrage rapide

Machine Linux (Ubuntu) sans prérequis. Suivre l'ordre, chaque étape dépend de la précédente. **[CLI]** = terminal, **[GUI]** = navigateur.

**Configuration minimale recommandée** : 4 CPU / 8 Go RAM. Avec moins (observé avec 1 CPU), les pods OpenFaaS peuvent rester bloqués en `Pending` faute de ressources.

### Étape 1 : Cloner

```bash
git clone https://github.com/exode-prog/Projet-PPP-Master-1-developpement-.git
cd Projet-PPP-Master-1-developpement-
```

### Étape 2 : Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker --version && docker compose version
```

### Étape 3 : Node.js (pour MCP Inspector)

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
```

### Étape 4 : Plateforme principale (axe 3 : gateway + Keycloak)

```bash
docker compose up -d
docker ps   # keycloak, mcp-gateway, mcp-target-server doivent être Up/healthy
```

Keycloak s'initialise seul (`scripts/keycloak_init.sh`) et peut mettre jusqu'à 2-3 min à devenir `healthy` sur machine chargée. Si `dependency failed to start: container keycloak is unhealthy` apparaît, attendre `healthy` dans `docker ps` puis relancer `docker compose up -d`.

### Étape 5 : Authentification : axe 3 **[CLI]**

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/realms/mcp-secure-platform/protocol/openid-connect/token \
  -d "client_id=mcp-target-server" -d "client_secret=$(sed -n '9p' scripts/keycloak_init.sh | grep -oP ':-\K[^}]+')" \
  -d "grant_type=password" -d "username=testuser" -d "password=test1234" \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -X POST http://127.0.0.1:9000/mcp \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Réponse `"serverInfo":{"name":"MCP Gateway - Sprint 6"...}` = axe 3 validé.

**[GUI]** optionnel : coller `Authorization: Bearer <TOKEN>` dans Headers de MCP Inspector avant connexion à `http://127.0.0.1:9000/mcp` (non persistant entre rechargements, démo ponctuelle seulement).

### Étape 5bis : RBAC — autorisation par rôle **[CLI]**

L'authentification JWT (étape 5) vérifie seulement qu'un token est valide, pas ce que son porteur a le droit de faire. Un deuxième rôle Keycloak (`mcp-admin`) et un deuxième utilisateur (`adminuser`, en plus de `testuser`) ont été ajoutés pour démontrer un vrai contrôle d'autorisation : l'outil `add` exige le rôle `mcp-admin`, l'outil `hello` reste ouvert à tout utilisateur authentifié (`mcp-user`).

```bash
# Obtenir un token pour chaque utilisateur (voir scripts/keycloak_init.sh pour la creation)
CLIENT_SECRET=$(docker exec keycloak /opt/keycloak/bin/kcadm.sh get clients/$( \
  docker exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r mcp-secure-platform -q clientId=mcp-target-server \
  | grep -o '"id" : "[^"]*"' | head -1 | sed 's/"id" : "//;s/"$//' \
)/client-secret -r mcp-secure-platform | grep -o '"value" : "[^"]*"' | sed 's/"value" : "//;s/"$//')

TOKEN_TEST=$(curl -s -X POST http://localhost:8080/realms/mcp-secure-platform/protocol/openid-connect/token \
  -d "client_id=mcp-target-server" -d "client_secret=$CLIENT_SECRET" \
  -d "grant_type=password" -d "username=testuser" -d "password=test1234" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# testuser (role mcp-user seul) -> add : REFUSE
curl -s -X POST http://127.0.0.1:9000/mcp -H "Authorization: Bearer $TOKEN_TEST" \
  -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"add","arguments":{"a":1,"b":2}}}'
# -> "Accès refusé : l'outil 'add' nécessite le rôle 'mcp-admin'"
```

Avec un token `adminuser` (rôle `mcp-admin` en plus), le même appel passe le contrôle de rôle (l'outil `add` demande ensuite une confirmation interactive, cf. élicitation Sprint 2). `hello` fonctionne pour les deux utilisateurs, sans restriction de rôle.

Implémentation : `src/gateway/gateway.py` (`ToolRoleRequirementMiddleware`). Remplace l'ancienne ébauche `src/target_server/auth.py` (Sprint 2, jamais branchée — supprimée).

### Étape 5ter : PKCE — protection du code d'autorisation **[CLI]**

Le flux OAuth2 Authorization Code classique est vulnerable au vol du `code` intermediaire (URL loggee, proxy, navigateur partage). PKCE ajoute un secret cote client (`code_verifier`) dont seule une empreinte SHA256 (`code_challenge`) est envoyee a Keycloak ; l'echange final du `code` contre un token exige le `code_verifier` original.

Le client `mcp-target-server` est configure pour l'exiger (`pkce.code.challenge.method=S256`) :

```bash
python3 scripts/test_pkce_flow.py valid    # code_verifier correct -> token obtenu
python3 scripts/test_pkce_flow.py invalid  # code_verifier errone  -> rejet explicite
# -> {"error":"invalid_grant","error_description":"PKCE verification failed: Code mismatch"}
```

### Étape 6 : gVisor (prérequis axe 1)

```bash
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gnupg
curl -fsSL https://gvisor.dev/archive.key | sudo gpg --yes --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | sudo tee /etc/apt/sources.list.d/gvisor.list > /dev/null
sudo apt-get update && sudo apt-get install -y runsc
sudo runsc install
sudo systemctl reload docker
docker run --rm --runtime=runsc hello-world
docker info | grep -A2 Runtimes   # doit lister "runsc"
```

Source : https://gvisor.dev/docs/user_guide/install

### Étape 7 : Démo sandbox : axe 1 **[CLI + GUI]**

```bash
docker compose -f docker-compose.vulnerable.yml up -d
docker compose -f docker-compose.vulnerable-hardened.yml up -d
```

IMPORTANT: Ne jamais lancer en dehors d'un réseau isolé ni fusionner avec `docker-compose.yml` : voir `src/vulnerable_server/README.md`.

- **[GUI]** Via MCP Inspector (étape 10) : outil `ping_host` sur port 8001 (sans protection) vs port 8002 (durci gVisor).
- **[CLI]** Vérification :
```bash
docker exec mcp-vulnerable-server-UNSAFE sh -c "cat /proc/1/status | grep CapEff"
docker exec mcp-vulnerable-server-HARDENED sh -c "cat /proc/1/status | grep CapEff"
docker exec mcp-vulnerable-server-UNSAFE sh -c "cat /proc/version"
docker exec mcp-vulnerable-server-HARDENED sh -c "cat /proc/version"
```

Protocole complet : `docs/demo-attaque-contenue.md`.

### Étape 7bis : Durcissement seccomp personnalisé + AppArmor (axe 1, cdc B.3/B.4/B.5) **[CLI]**

En plus du profil seccomp par défaut de Docker, un profil **personnalisé** retire 22 syscalls supplémentaires (`ptrace`, `mount`, `umount2`, `reboot`, modules noyau, `bpf`, `process_vm_readv/writev`, etc.) et un profil **AppArmor** personnalisé restreint l'accès fichiers/réseau/capacités (`deny /etc/shadow`, `deny /root/**`, `deny /var/run/docker.sock`, `deny ptrace`, `deny capability`).

```bash
# Generer le profil seccomp durci (base : profil Docker par defaut)
curl -L -o security/seccomp-default.json https://raw.githubusercontent.com/moby/moby/v25.0.0/profiles/seccomp/default.json
python3 scripts/build_seccomp_hardened.py   # retire les syscalls dangereux -> security/seccomp-hardened.json

# Charger le profil AppArmor dans le noyau hote
sudo cp security/apparmor-mcp-vulnerable-hardened.profile /etc/apparmor.d/mcp-vulnerable-hardened
sudo apparmor_parser -r /etc/apparmor.d/mcp-vulnerable-hardened
sudo aa-status | grep mcp-vulnerable-hardened
```

Les deux profils sont référencés dans `docker-compose.vulnerable-hardened.yml` via `security_opt`.

**Constat important** : sous `runtime: runsc` (gVisor), ces profils ne sont **pas évalués par le noyau hôte** — gVisor les rend inopérants car il intercepte les appels dans son propre espace utilisateur (le Sentry), sans déclencher les hooks seccomp/AppArmor classiques (confirmé par l'absence de logs `apparmor="DENIED"` malgré un accès réussi à `/etc/shadow`). Ils ont donc été validés séparément sous le runtime standard (`runc`) :

```bash
docker compose -f docker-compose.vulnerable-seccomp-apparmor-test.yml up -d --build

# Ces trois commandes doivent echouer (BLOQUE) :
docker exec mcp-vulnerable-server-SECCOMP-APPARMOR-TEST python3 -c "import ctypes; print(ctypes.CDLL('libc.so.6', use_errno=True).ptrace(0,0,0,0))"
docker exec mcp-vulnerable-server-SECCOMP-APPARMOR-TEST mount -t tmpfs tmpfs /mnt
docker exec mcp-vulnerable-server-SECCOMP-APPARMOR-TEST cat /etc/shadow

# Confirmation dans les logs noyau
sudo dmesg | grep "mcp-vulnerable-hardened"
```

Détails et nuance gVisor/runc : `docs/vulnerabilite-sprint3.md`.

### Étape 8 : k3s + OpenFaaS (prérequis axe 2)

```bash
curl -sfL https://get.k3s.io | sh -

mkdir -p ~/.kube
sudo k3s kubectl config view --raw > ~/.kube/config
chmod 600 ~/.kube/config
export KUBECONFIG=~/.kube/config
echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc

curl -sLS https://get.arkade.dev | sh
sudo cp arkade /usr/local/bin/arkade && sudo ln -sf /usr/local/bin/arkade /usr/local/bin/ark && rm -f arkade

arkade install openfaas --set openfaasPro=false --operator=false
```

`--set openfaasPro=false --operator=false` est obligatoire (sinon édition Pro bloquée faute de licence).

### Étape 9 : Démo serverless : axe 2 **[CLI + GUI]**

```bash
kubectl port-forward -n openfaas svc/gateway 31112:8080 > /tmp/pf-gateway.log 2>&1 &
disown
sleep 3
export OPENFAAS_URL=http://127.0.0.1:31112

arkade get faas-cli
sudo mv ~/.arkade/bin/faas-cli /usr/local/bin/ 2>/dev/null || true

PASSWORD=$(kubectl get secret -n openfaas basic-auth -o jsonpath="{.data.basic-auth-password}" | base64 --decode)
faas-cli login --gateway $OPENFAAS_URL -u admin -p "$PASSWORD"
faas-cli template store pull python3-http
faas-cli deploy -f stack.yaml --gateway $OPENFAAS_URL
curl -X POST $OPENFAAS_URL/function/mcp-server-function -d '{}'
```

**[GUI]** : ouvrir `http://127.0.0.1:31112/ui/` avec `admin` / `$PASSWORD` ci-dessus, invoquer `mcp-server-function` depuis l'interface.

### Étape 9 : Cycle éphémère automatique via LocalStack **[CLI]**

Contrairement à OpenFaaS (scale manuel), LocalStack émule AWS Lambda avec un cycle de vie réellement automatique. Détail : `docs/axe2-scale-to-zero.md`.

`.env.localstack` (ignoré par git) **obligatoire** : compte gratuit sur https://app.localstack.cloud, puis `echo "LOCALSTACK_AUTH_TOKEN=<token>" > .env.localstack`.

```bash
# Installer awslocal/aws si absents (pip ancien : --user, pas --break-system-packages)
pip3 install --user awscli-local awscli
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

docker compose -f docker-compose.localstack.yml up -d
sleep 10

export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

awslocal lambda create-function \
  --function-name mcp-lambda-function \
  --runtime python3.12 --handler handler.handler \
  --zip-file fileb://localstack-lambda/function.zip \
  --role arn:aws:iam::000000000000:role/lambda-role

for i in {1..15}; do
  STATE=$(awslocal lambda get-function --function-name mcp-lambda-function --query 'Configuration.State' --output text)
  [ "$STATE" = "Active" ] && break
  sleep 2
done

docker ps   # avant
awslocal lambda invoke --function-name mcp-lambda-function output.json
cat output.json
docker ps   # après : conteneur public.ecr.aws/lambda/python:3.12 présent

watch -n 5 docker ps   # observer la disparition automatique (~20 min)
```

### Étape 10 : Démonstration visuelle **[GUI]** (MCP Inspector)

```bash
npx @modelcontextprotocol/inspector
```

Cliquer **« Ajouter des serveurs »** (l'accueil affiche des serveurs d'exemple préconfigurés, pas un état vide). Transport **Streamable HTTP** → `http://127.0.0.1:8001/mcp` (sans protection) ou `http://127.0.0.1:8002/mcp` (durci).

### Étape 11 (optionnelle) : Ollama comme hôte MCP autonome

Complément à MCP Inspector (A.5). Démontre le consentement humain (HIL) avant exécution d'outil.

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:3b
python3 -m venv MCP-PPP && source MCP-PPP/bin/activate
pip install mcp-client-for-ollama
ollmcp -u http://127.0.0.1:8001/mcp -m qwen2.5:3b
```

ollmcp demande confirmation (`Allow this tool call? [y/n]`) avant tout appel d'outil  c'est le consentement explicite exigé par le cdc A.6. Détail : `docs/demo-ollama.md`.

### Tout arrêter

```bash
docker compose down
docker compose -f docker-compose.vulnerable.yml down
docker compose -f docker-compose.vulnerable-hardened.yml down
```

## Structure du dépôt : Documentation technique (`docs/`)

| Document | Contenu |
|---|---|
| `gateway-sprint6.md` | Conteneurisation de la gateway |
| `vulnerabilite-sprint3.md` | Vulnérabilité CWE-78 du serveur cible |
| `comparatif-gvisor-firecracker.md` | Comparaison technologique sandbox |
| `demo-attaque-contenue.md` | Preuve empirique du scénario B.2 |
| `demo-ollama.md` | Démo Ollama/ollmcp |
| `no-egress-sprint5.md` | Limitation NetworkPolicy k3s |
| `integration-3-axes.md` | Articulation des 3 axes |
| `axe2-scale-to-zero.md` | Investigation scale-to-zero |
| `tco.md` | Calcul du coût réel (TCO), sourcé |
| `sprint7-finalisation.md` | Synthèse finalisation |

## Développement (contributeurs)

```bash
sudo apt update && sudo apt install git python3-venv -y
python3 -m venv MCP-PPP && source MCP-PPP/bin/activate
pip install --upgrade pip && pip install fastmcp
```

## Difficultés et limites rencontrées

| Difficulté | Traitement |
|---|---|
| Scale-to-zero OpenFaaS indisponible (édition Pro uniquement) | Cycle manuel (`spawn.sh`/`teardown.sh`) + preuve via LocalStack. `docs/axe2-scale-to-zero.md` |
| Knative : bug DNS bloquant chronique | Abandonné et documenté avec cause racine. `docs/axe2-scale-to-zero.md` |
| NetworkPolicy no-egress non supportée par Flannel (CNI k3s) | Limitation assumée, isolation reposant sur la séparation réseau Docker de l'axe 1. `docs/no-egress-sprint5.md` |
| Keycloak `Exited (255)` sans trace applicative | Diagnostiqué par élimination, relancé et revalidé |
| Variabilité mesure cold-start gVisor (6,8%–120%) | Présenté comme plage mesurée, pas un chiffre unique. `docs/tco.md` |
| Headers non persistants dans MCP Inspector | Auth documentée en test CLI obligatoire (curl), GUI pour démo ponctuelle seulement |
| Proxy serverless : réponse statique, pas de vraie session MCP relayée | Docstring corrigé, portée clarifiée comme preuve de concept |
| Install gVisor : ancien binaire seul obsolète (404), doc officielle imprécise sur le chemin | Méthode APT substituée, chemin vérifié (`dpkg -L runsc`) et testé fonctionnellement |
| arkade échoue parfois à s'installer dans `/usr/local/bin` | Repli manuel documenté (Étape 8) |
| Réinstallation OpenFaaS : conflit RBAC Helm (`roleRef` immuable) | Rollback Helm vers révision stable |
| Keycloak healthcheck trop court sur machine chargée | Pas un échec réel ; relancer `docker compose up -d` une fois `healthy` |
| Kubeconfig root-only | Copié vers `~/.kube/config` (Étape 8) |
| arkade installe OpenFaaS Pro par défaut | `--set openfaasPro=false --operator=false` obligatoire |
| `awslocal` nécessite un vrai `aws` CLI | `pip install awscli` en complément de `awscli-local` |
| `.env.localstack` devenu obligatoire avec l'image `:latest` | Corrigé à l'Étape 9bis après preuve empirique sur 2e machine |
| MCP Inspector affiche des serveurs d'exemple par défaut | Clarifié à l'Étape 10 : cliquer « Ajouter des serveurs » |


