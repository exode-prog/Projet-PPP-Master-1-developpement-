# Intégration des trois axes techniques

## Contexte

Le cahier des charges (Partie B.1) demande une "plateforme d'exécution
sécurisée globale" articulant trois axes :

- **Axe 1** — Isolation par sandbox (gVisor vs Firecracker)
- **Axe 2** — Architecture serverless et cycle de vie éphémère
- **Axe 3** — Gateway et orchestration (authentification, quotas, audit)

Ce document fait le bilan de l'état réel de chaque axe (vérifié en direct le
2026-10-03, voir `docs/gateway-sprint6.md`, `docs/demo-attaque-contenue.md`,
`docs/no-egress-sprint5.md`) et explique le choix architectural retenu pour
les faire cohabiter.

## Choix architectural : intégration légère ("Option A")

Les trois axes sont **volontairement maintenus séparés** plutôt que fusionnés
dans un unique `docker-compose.yml` ou une unique codebase. Chaque axe
dispose de son propre moyen de déploiement et de sa propre preuve :

| Axe | Déploiement | Preuve |
|---|---|---|
| 1 — Sandbox | `docker-compose.vulnerable.yml` / `docker-compose.vulnerable-hardened.yml` (jamais fusionnés au compose principal) | `docs/demo-attaque-contenue.md` |
| 2 — Serverless | k3s + OpenFaaS (`stack.yaml`, namespace `openfaas-fn`) + LocalStack (`docker-compose.localstack.yml`) | ce document |
| 3 — Gateway | `docker-compose.yml` (Keycloak, gateway, target-server) | `docs/gateway-sprint6.md` |

Cette séparation n'est pas un manque d'intégration mais une décision
assumée dès le Sprint 3 (voir la règle du projet : "Ne jamais fusionner
avec le docker-compose.yml principal"), pour deux raisons :

1. **Sécurité** : le serveur volontairement vulnérable (axe 1) ne doit
   jamais partager un réseau Docker avec la plateforme réelle.
2. **Isolation des préoccupations** : chaque axe répond à une exigence
   distincte du cahier des charges et se valide indépendamment ; les
   fusionner masquerait quel composant prouve quoi.

Le lien entre les axes est donc **documentaire et conceptuel**, pas une
intégration par appel réseau : aucun code de `src/gateway` ou
`src/target_server` n'invoque l'infrastructure OpenFaaS ou les conteneurs
du Sprint 3/4 (vérifié par recherche dans le code source — aucune
occurrence de "openfaas"/"faas" dans `src/`). Chaque axe est un module de
preuve autonome de la même plateforme conceptuelle.

## État vérifié de chaque axe (2026-10-03)

### Axe 1 — Sandbox (gVisor)

Fonctionnel et mesuré. Cold-start +14 %, RAM/CPU légèrement supérieurs en
conteneur gVisor, mais capacités Linux effectives (`CapEff`) ramenées à
zéro et écriture/exécution hors `/tmp` bloquées, alors que l'injection de
commande applicative (CWE-78) reste identiquement exploitable dans les deux
cas — conforme au principe du projet : on ne corrige pas le code
vulnérable, on contient ses conséquences au niveau infrastructure. Détail
complet : `docs/demo-attaque-contenue.md`.

### Axe 2 — Serverless et cycle de vie éphémère

- **k3s** : un nœud `control-plane`, actif depuis 2j12h, sain.
- **OpenFaaS** : déployé dans les namespaces `openfaas`/`openfaas-fn`,
  fonction `mcp-server-function` (template `python3-http`) en cours
  d'exécution. Testée en direct via le NodePort `31112`, en CLI (`curl`)
  et en GUI (portail web OpenFaaS, authentification basique) : réponse
  HTTP 200, `{"message": "Fonction serverless MCP active", ...}`. Le
  handler (`build/mcp-server-function/function/handler.py`) démontre le
  principe du déploiement et de l'invocation serverless — **c'est une
  preuve de concept du mécanisme serverless, pas un relais complet vers un
  serveur MCP** : le code renvoie une confirmation statique plutôt que de
  proxyfier une vraie session MCP. Le docstring du handler ("transmet la
  requête au serveur MCP interne") est à ce titre plus ambitieux que
  l'implémentation réelle ; ce document corrige cette description pour
  rester fidèle au code.
- **Scale-to-zero sur OpenFaaS : non disponible.** C'est une
  fonctionnalité réservée à l'édition Pro (confirmé par la documentation
  officielle), reconfirmé empiriquement le 2026-10-04 : le déploiement
  tourne en continu depuis 3 jours sans interruption (`kubectl get
  deploy`), aucun scale-down observé. Une alternative, Knative, a été
  testée et abandonnée pour un bug DNS chronique et bloquant
  (`activator` → `autoscaler`). Le projet retient donc un cycle de vie
  **manuel** via `spawn.sh`/`teardown.sh` (scale 0 ↔ 1) pour l'axe 2
  principal. Détail complet, tableau comparatif et causes racines :
  `docs/axe2-scale-to-zero.md`.
- **NetworkPolicy no-egress** : définie (`no-egress-policy.yaml`) mais
  **non appliquée en pratique**, le CNI Flannel par défaut de k3s ne
  supportant pas les NetworkPolicy. Limitation assumée et documentée dans
  `docs/no-egress-sprint5.md` (Calico/Cilium aurait permis l'application
  réelle, mais l'isolation réseau du projet repose déjà sur la séparation
  des réseaux Docker de l'axe 1, jugée suffisante pour la démonstration).
- **LocalStack (preuve complémentaire du cycle éphémère automatique)** :
  à la différence d'OpenFaaS, LocalStack (émulation du runtime AWS Lambda)
  démontre un cycle de vie réellement automatique et sans intervention
  manuelle — conteneur créé à l'invocation, détruit tout seul après
  inactivité, confirmé empiriquement par observation directe
  (`docker ps` avant/après + `watch`). Protocole complet et résultats :
  `docs/axe2-scale-to-zero.md`.

### Axe 3 — Gateway et orchestration

Entièrement conteneurisé depuis la finalisation du `docker-compose.yml`
(Sprint 6) : Keycloak, gateway, target-server démarrent via une seule
commande (`docker compose up -d`). Authentification JWT (issuer/JWKS),
quotas glissants et audit log fonctionnels de bout en bout — revérifié en
direct le 2026-10-03 après une interruption d'infrastructure externe
(Keycloak arrêté silencieusement ~15h avant, cause probable : redémarrage
de la VM ou du démon Docker, aucune trace d'erreur applicative) : relance
via `docker compose up -d`, conteneur `Healthy` en 21,9 s, token Keycloak
obtenu et appel `initialize` accepté par la gateway (`MCP Gateway - Sprint
6 v4.0.10`). Détail complet : `docs/gateway-sprint6.md`.

## Conclusion

Les trois axes du cahier des charges sont chacun fonctionnels et prouvés
indépendamment, assemblés sous une architecture d'intégration légère
(Option A) qui préserve l'isolation de sécurité entre le composant
volontairement vulnérable et la plateforme réelle, tout en démontrant
séparément le sandboxing (axe 1), le cycle de vie éphémère serverless
(axe 2) et l'orchestration sécurisée via gateway (axe 3).
