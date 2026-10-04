# Investigation scale-to-zero et cycle de vie éphémère (axe 2)

## Contexte

L'axe 2 du cahier des charges (B.1) exige une démonstration du cycle de vie
éphémère d'une architecture serverless : un composant qui n'existe pas tant
que personne ne l'appelle, créé à la demande, et détruit automatiquement
après inactivité. Ce document consolide l'investigation menée au Sprint 5
sur trois solutions différentes pour obtenir ce comportement, leurs
résultats réels, et la décision retenue pour le reste du projet.

Référence du travail initial : commit `1a290a3` ("Sprint 5 : architecture
serverless (OpenFaaS, LocalStack, cycle de vie ephemere)").

## Tableau comparatif final

| Critère | OpenFaaS (Community Edition) | Knative Serving |
|---|---|---|
| Statut dans le projet | Retenu — déploiement fonctionnel validé | Écarté — bug bloquant non résolu |
| Déploiement de la fonction | Fonctionnel (image publique `exode1/mcp-server-function`, `faas-cli deploy` réussi) | N'atteint pas l'état `Ready` — l'activateur ne peut pas router les requêtes vers l'autoscaler |
| Scale-to-zero | Non disponible en Community Edition (fonctionnalité Pro, confirmé par la documentation officielle) | Nativement prévu par l'architecture, mais inopérant dans cet environnement à cause d'un bug DNS |
| Cause racine identifiée | Limitation commerciale assumée par l'éditeur (restriction de licence Community/Pro) | Bug technique chronique de résolution DNS interne (activator → autoscaler), documenté depuis 2019 |
| Reproductibilité du problème | Totale et prévisible (comportement documenté, cohérent à chaque test) | Totale sur cet environnement (28 échecs identiques sur 144 minutes) |
| Pistes testées | Scale manuel, annotation `com.openfaas.scale.min`, recherche de logs d'idler sur le cluster | DNS (CoreDNS), ressources CPU/RAM, ingress Kourier, délai de démarrage → 4 hypothèses éliminées une à une |
| Environnement de test | VM principale du projet (DevSecOps-Cloud) | VM clonée (« clone de preuve ») pour ne pas risquer l'environnement principal |
| Sources | docs.openfaas.com/openfaas-pro/scale-to-zero/ ; GitHub openfaas/faas #978, #979 | GitHub knative/serving #5542, #11544, #15171, #18530 |
| Décision finale | Solution retenue pour le Sprint 5 : cycle de vie manuel `spawn.sh` → `teardown.sh` (scale manuel 0 → 1) | Piste abandonnée ; documentée comme contrainte technique rencontrée et justifiée |

Reconfirmation empirique (2026-10-04) : le déploiement `mcp-server-function`
tourne en continu depuis 3 jours sans interruption (`kubectl get deploy`,
pod `Running` depuis 135 minutes au moment du contrôle), ce qui recoupe
exactement la limitation documentée ci-dessus — aucun scale-down observé.

## Preuve empirique du cycle de vie éphémère réel : LocalStack (émulation Lambda)

Face à l'indisponibilité du scale-to-zero sur les deux solutions
principales, le cycle de vie éphémère complet (création à l'invocation,
destruction automatique après inactivité) a été démontré séparément via
LocalStack, qui émule le runtime AWS Lambda officiel localement.

### Protocole (rejoué et vérifié le 2026-10-04)

1. Démarrage du conteneur LocalStack :
```bash
   docker compose -f docker-compose.localstack.yml up -d
```
2. (Re)création de la fonction — l'état de LocalStack n'étant pas persistant
   (pas de volume de données dans `docker-compose.localstack.yml`), la
   fonction doit être redéployée à chaque redémarrage du conteneur :
```bash
   awslocal lambda create-function \
     --function-name mcp-lambda-function \
     --runtime python3.12 \
     --handler handler.handler \
     --zip-file fileb://localstack-lambda/function.zip \
     --role arn:aws:iam::000000000000:role/lambda-role
```
3. État juste avant invocation (`docker ps`) : seuls `localstack-mcp` et
   `local-registry` tournent, aucun conteneur dédié à la fonction.
4. Invocation :
```bash
   awslocal lambda invoke --function-name mcp-lambda-function output.json
```
   Résultat : `{"StatusCode": 200, "ExecutedVersion": "$LATEST"}`
5. Contenu de `output.json` :
{"statusCode": 200, "body": "{"message": "Fonction Lambda MCP via LocalStack", "note": "Demonstration du cycle de vie ephemere serverless (Sprint 5)"}"}
6. État juste après invocation (`docker ps`) : nouveau conteneur
   `localstack-mcp-lambda-mcp-lambda-function-b376c4f90998de39537617147b37d052`,
   image `public.ecr.aws/lambda/python:3.12` (runtime Lambda officiel AWS),
   créé à l'instant ("2 seconds ago").
7. `watch -n 5 docker ps` laissé tourner sans nouvelle invocation : après
   environ 22 minutes, le conteneur de la fonction a disparu de lui-même ;
   seuls `localstack-mcp` (up 22 min) et `local-registry` restent — état
   identique à l'étape 3, sans aucune intervention manuelle.

### Incident rencontré et corrigé pendant le test

Le premier essai d'invocation a échoué avec
`ResourceConflictException: ... The function is currently in the following
state: Pending`, car la vérification d'état utilisait un délai fixe
(`sleep 5`) trop court — LocalStack n'avait pas fini d'initialiser la
fonction. Corrigé en remplaçant le délai fixe par une boucle qui attend
l'état `Active` réel avant d'invoquer, plutôt que de supposer qu'un délai
arbitraire suffit — cohérent avec la méthodologie du projet : vérifier
l'état réel plutôt que deviner un résultat.

### Interprétation

Ce test démontre un cycle de vie réellement éphémère et **entièrement
automatique**, sans script ni intervention manuelle (contrairement à
`spawn.sh`/`teardown.sh` sur OpenFaaS, qui nécessitent une action
explicite à chaque changement d'état) :

- le conteneur d'exécution n'existe pas tant que la fonction n'est pas
  invoquée ;
- il est créé à la volée au moment de l'invocation, avec le runtime AWS
  Lambda officiel ;
- il se termine de lui-même après une période d'inactivité, sans qu'aucune
  commande ne soit lancée pour le détruire.

C'est la preuve que le modèle serverless à cycle de vie éphémère est un
concept réalisable et reproductible, même si la stack principale retenue
pour le projet (OpenFaaS sur k3s, Community Edition) ne permet pas de
l'obtenir automatiquement.

## Conclusion

L'axe 2 est fonctionnel pour le déploiement et l'invocation d'une fonction
serverless (OpenFaaS sur k3s, testé en CLI et en GUI). La caractéristique
spécifique de scale-to-zero automatique n'a pas pu être démontrée sur la
stack principale du projet : deux solutions candidates (OpenFaaS CE,
Knative) ont été testées et ont chacune révélé une limitation différente,
documentée avec sa cause racine plutôt que contournée en silence. Le
concept lui-même reste validé par la preuve empirique obtenue via
LocalStack/Lambda, qui démontre qu'un cycle de vie réellement éphémère
(création et destruction automatiques sans intervention) est bien
réalisable dans l'écosystème serverless, même s'il n'a pas pu être
reproduit sur la stack k3s/OpenFaaS retenue pour le reste du projet.
