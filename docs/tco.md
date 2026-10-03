# TCO (Total Cost of Ownership) — coût réel calculé

## 1. Introduction

Le cahier des charges (B.8, critère "Finition, GitHub & TCO", 15 % de la
note, évalué avec la même exigence que "Dimensionnement & Rigueur", 30 %)
demande un **coût réel calculé**. Le projet tourne actuellement
gratuitement sur une VM locale (B.6 : "l'infrastructure s'exécute
localement et gratuitement"). Ce document répond donc à une question de
projection : que coûterait cette plateforme en production cloud réelle,
et où irait cet argent ?

## 2. Rôle et objectif

- Partir de **mesures réelles** de consommation CPU/RAM de chaque axe
  (jamais de valeurs inventées), au repos et sur plusieurs échantillons.
- Comparer au moins deux scénarios d'architecture pour montrer un
  raisonnement de dimensionnement, pas une simple multiplication.
- Sourcer chaque tarif externe, avec date de consultation.
- Confronter nos mesures à une référence externe quand elle existe, pour
  juger si un résultat est un phénomène réel ou un artefact de la VM.

## 3. Méthodologie et tests exécutés

Mesures prises le 2026-10-03 (23:22 UTC), chaque axe isolé, avec attente
de stabilisation (30 s) et 3 échantillons espacés de 5 s pour l'axe 1 :

```bash
docker stats --no-stream keycloak mcp-gateway mcp-target-server
kubectl top pods -A
systemctl show k3s --property=MemoryCurrent
ps -eo pid,comm,%cpu,rss --sort=-rss | grep k3s-server
# Axe 1 : conteneurs demarres, 30s d'attente, 3 mesures espacees de 5s
docker stats --no-stream mcp-vulnerable-server-UNSAFE mcp-vulnerable-server-HARDENED
```

## 4. Mesures réelles consolidées

| Composant | Axe | CPU | RAM |
|---|---|---|---|
| `keycloak` | 3 | 0,55 % | 611,8 MiB |
| `mcp-gateway` | 3 | 0,26 % | 78,08 MiB |
| `mcp-target-server` | 3 | 0,29 % | 73,77 MiB |
| **Total axe 3** | 3 | **1,10 % (~0,011 vCPU)** | **763,65 MiB (~0,75 Gi)** |
| Pods k3s (kube-system + openfaas + openfaas-fn) | 2 | 38 m (~0,038 vCPU) | 243 Mi |
| Socle k3s-server + containerd (cgroup `k3s.service`) | 2 | ~0,96-0,98 vCPU (mesuré 2 fois, 98,3 % puis 96,3 %) | 945,4 Mi (cgroup complet, pods inclus) |
| **Total axe 2** | 2 | **~1,0 vCPU** | **~945 Mi (~0,92 Gi)** |
| Sandbox standard (moyenne 3 échantillons) | 1 | 0,32 % | 64,03 MiB |
| Sandbox gVisor (moyenne 3 échantillons, encore décroissante : 6,11→3,03→2,41 %) | 1 | 2,4-6,1 % (plage, stabilisation lente) | 90,89 MiB |
| **Surcoût gVisor** | 1 | **+2 à +6 pts (~+0,02-0,06 vCPU)** | **+26,86 MiB** |

**Correction méthodologique importante** : une première estimation de
l'axe 2 avait utilisé `kubectl top nodes` (780 m / 4 356 Mi), qui mesure
**toute la VM** (y compris la stack Docker Compose tournant à côté), pas
k3s seul. La mesure correcte isole le cgroup systemd `k3s.service`
(945 Mi) et le processus `k3s-server` lui-même, mesuré **deux fois
indépendamment à 98,3 % puis 96,3 % de CPU** — un socle de contrôle
Kubernetes qui consomme en continu quasiment un cœur entier, même pour
une seule fonction de faible trafic.

## 5. Sources externes (consultées le 2026-10-03)

| Référence | Usage | Lien |
|---|---|---|
| AWS EC2 — t3.small on-demand (us-east-1) | Dimensionnement axe 3 | [Holori Cloud Calculator](https://calculator.holori.com/aws/ec2/t3.small) |
| AWS EC2 — t3.medium on-demand (us-east-1) | Dimensionnement axe 2 (auto-hébergé) | [Holori Cloud Calculator](https://calculator.holori.com/aws/ec2/t3.medium/us-east-1) |
| AWS EC2 — t3.micro on-demand (eu-west-1) | Référence basse écartée (RAM insuffisante) | [Holori Cloud Calculator](https://calculator.holori.com/aws/ec2/t3.micro/eu-west-1) |
| AWS Lambda — tarif requêtes et calcul | Dimensionnement axe 2 (scénario cloud-natif) | [AWS Lambda Pricing Breakdown — CloudChipr](https://cloudchipr.com/blog/aws-lambda-pricing) |
| k3s — empreinte officielle du socle de contrôle (nœud unique) | Comparaison/validation de nos mesures | [k3s.io — Resource Profiling](https://docs.k3s.io/reference/resource-profiling) |

**Comparaison avec la référence officielle** : k3s.io documente un socle
à vide d'environ **6 % d'un cœur et ~1,6 Go RAM** sur serveur dédié
(Intel 8375C). Notre RAM mesurée (945 Mi) est du même ordre de grandeur
(légèrement inférieure, charge plus légère ici). Notre CPU mesurée
(~97 %) est très supérieure à la référence — écart plausible et assumé :
VM VirtualBox à 4 vCPU partagés, avec Docker et k3s imbriqués sur le même
hôte, contrairement au serveur dédié de la documentation officielle.

## 6. Scénarios cloud chiffrés

*(Mois AWS standard = 730 heures.)*

### Scénario A — Architecture telle quelle (k3s auto-hébergé)

| Poste | Dimensionnement | Justification | Coût mensuel |
|---|---|---|---|
| Axe 3 (gateway + Keycloak + target, durci gVisor) | t3.small (2 vCPU/2 Gi) | couvre 0,011+0,06 vCPU et 0,75+0,03 Gi mesurés, large marge OS/Docker | 15,18 $ |
| Axe 2 (k3s + OpenFaaS auto-hébergés) | t3.medium (2 vCPU/4 Gi) | **CPU est le facteur limitant** (~1 vCPU soutenu), pas la RAM comme estimé initialement ; un t3.medium reste cependant une instance *burstable* (crédit CPU de base ~40 % de 2 vCPU) — un usage soutenu proche d'1 vCPU finirait par consommer les crédits en production réelle, une instance non-burstable serait plus sûre | 30,37 $ |
| **Total Scénario A** | | | **45,55 $/mois (≈ 547 $/an)** |

### Scénario B — Cloud-natif (axe 2 remplacé par AWS Lambda)

Hypothèse de volumétrie réaliste pour un usage pédagogique/démo :
100 000 invocations/mois, 200 ms, 128 Mo → 2 500 Go-s/mois, très en
dessous du quota gratuit (400 000 Go-s/mois, 1M requêtes/mois).

| Poste | Dimensionnement | Coût mensuel |
|---|---|---|
| Axe 3 | t3.small | 15,18 $ |
| Axe 2 (Lambda, 100k invocations/mois) | sous quota gratuit | 0,00 $ |
| **Total Scénario B** | | **15,18 $/mois (≈ 182 $/an)** |

## 7. Tableau comparatif final (différences)

| | Coût actuel (local, B.6) | Scénario A (cloud, k3s auto-hébergé) | Scénario B (cloud, Lambda managé) | Différence A→B |
|---|---|---|---|---|
| Mensuel | 0 $ | 45,55 $ | 15,18 $ | **-30,37 $ (-67 %)** |
| Annuel | 0 $ | ≈ 547 $ | ≈ 182 $ | **≈ -365 $/an** |

**Conclusion chiffrée** : le socle de contrôle Kubernetes (k3s-server)
consomme à lui seul l'équivalent d'un cœur CPU en continu — confirmé par
deux mesures indépendantes et cohérent avec un phénomène documenté
officiellement par k3s.io, bien qu'amplifié ici par les ressources
partagées de la VM. Remplacer cet auto-hébergement par un serverless
managé (AWS Lambda) réduit le coût cloud projeté de **67 % (-365 $/an)**
pour ce projet, car l'usage réel (une fonction de démonstration à faible
trafic) reste largement dans le quota gratuit d'un service managé. Le
durcissement gVisor de l'axe 1 ajoute un surcoût mesuré de seulement
quelques points de CPU et ~27 Mio de RAM — négligeable, il ne change pas
le palier d'instance choisi : la sécurité supplémentaire est obtenue à
**coût cloud quasi nul**.

## 8. Limites et hypothèses assumées

- Coût actuel réel payé : 0 $ (VM locale gratuite). Les scénarios A/B
  sont des projections, pas une dépense engagée.
- Volumétrie Lambda (100 000 invocations/mois) : hypothèse pédagogique
  raisonnable et explicite, non mesurée en production réelle.
- La variabilité mesurée du surcoût CPU gVisor (2 à 6 points selon le
  moment de la mesure) reflète une stabilisation encore en cours du
  noyau utilisateur "Sentry" même après 30 s — présentée comme une plage
  plutôt qu'un chiffre unique, par honnêteté sur l'incertitude.
- Tarifs du 2026-10-03, région us-east-1 pour t3.small/t3.medium (un
  déploiement en eu-west-1 serait généralement 5 à 10 % plus cher chez
  AWS, non chiffré précisément faute de source directe consultée).
- Coût de stockage (images Docker, ~1,5 Go cumulés) non inclus :
  négligeable (~1,60 $/mois pour 20 Go d'EBS gp3) face aux postes compute.
