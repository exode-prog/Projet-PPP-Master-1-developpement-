# TCO (Total Cost of Ownership) — coût réel calculé

## Méthodologie

Calcul **bottom-up** : mesure réelle de la consommation CPU/RAM de chaque
composant (via `docker stats` et `kubectl top`, relevés le 2026-10-03, voir
`docs/integration-3-axes.md`), puis conversion en dimensionnement cloud
équivalent et chiffrage avec la tarification publique AWS en vigueur
(sources citées, consultées le 2026-10-03). Le projet s'exécutant
actuellement gratuitement sur une VM locale (B.6 du cahier des charges),
ce document répond à la question : **"que coûterait un déploiement réel
de cette plateforme en production cloud ?"**

## 1. Mesures réelles consolidées

| Composant | Axe | CPU mesuré | RAM mesurée |
|---|---|---|---|
| `keycloak` | 3 | 7,39 % (~0,074 vCPU) | 606,2 MiB |
| `mcp-gateway` | 3 | 0,28 % (~0,003 vCPU) | 77,97 MiB |
| `mcp-target-server` | 3 | 0,26 % (~0,003 vCPU) | 85,82 MiB |
| Surcout gVisor (si target-server durci, delta mesuré sur le serveur vulnerable) | 1 | +6,40 % (~0,064 vCPU) | +27,97 MiB |
| Cluster k3s complet (nœud) | 2 | 780 m (0,78 vCPU, 19 %) | 4 356 MiB (54 %) |
| — dont fonction `mcp-server-function` seule | 2 | 9 m (0,009 vCPU) | 27 MiB |
| — dont socle Kubernetes (CoreDNS, Traefik, OpenFaaS control-plane...) | 2 | 771 m (0,771 vCPU, **98,8 %** du nœud) | 4 329 MiB (**99,4 %** du nœud) |

**Constat de rigueur** : auto-héberger un cluster k3s pour exécuter une
seule fonction serverless de faible trafic revient à payer en continu
pour un socle Kubernetes qui représente ~99 % de la charge — l'inverse du
principe serverless ("payer à l'usage"). Ce constat oriente le calcul
ci-dessous vers deux scénarios comparés.

## 2. Tarifs sourcés (AWS, consultés le 2026-10-03)

| Ressource | Prix | Source |
|---|---|---|
| EC2 t3.micro (2 vCPU, 1 GiB, Linux, eu-west-1) | 0,0114 $/h | [Holori Cloud Calculator](https://calculator.holori.com/aws/ec2/t3.micro/eu-west-1) |
| EC2 t3.small (2 vCPU, 2 GiB, Linux, us-east-1) | 0,0208 $/h | [Holori Cloud Calculator](https://calculator.holori.com/aws/ec2/t3.small) |
| EC2 t3.medium (2 vCPU, 4 GiB, Linux, us-east-1) | 0,0416 $/h | [Holori Cloud Calculator](https://calculator.holori.com/aws/ec2/t3.medium/us-east-1) |
| AWS Lambda — requêtes | 0,20 $ / 1 million | [AWS Lambda Pricing Breakdown — CloudChipr](https://cloudchipr.com/blog/aws-lambda-pricing) |
| AWS Lambda — calcul | 0,0000166667 $ / Go-seconde (palier 1, jusqu'à 6 Md Go-s/mois) | [AWS Lambda Pricing Breakdown — CloudChipr](https://cloudchipr.com/blog/aws-lambda-pricing) |
| AWS Lambda — quota gratuit mensuel | 1 million de requêtes + 400 000 Go-secondes | idem |

*(Hypothèse de calcul : mois AWS standard = 730 heures.)*

## 3. Scénario A — "Lift-and-shift" (architecture actuelle telle quelle)

Déploiement qui reproduit tel quel l'architecture du projet (Option A,
axes séparés), sans repenser l'axe 2 :

| Poste | Dimensionnement | Calcul | Coût mensuel |
|---|---|---|---|
| Axe 3 (gateway + Keycloak + target-server, durci gVisor) | t3.small (2 vCPU/2 Gi — couvre les ~0,14 vCPU / ~0,78 Gi mesurés avec marge OS/Docker) | 0,0208 $/h × 730 h | **15,18 $** |
| Axe 2 (cluster k3s + OpenFaaS auto-hébergés) | t3.medium (2 vCPU/4 Gi — couvre les 0,78 vCPU / 4,3 Gi mesurés) | 0,0416 $/h × 730 h | **30,37 $** |
| **Total Scénario A** | | | **45,55 $/mois (≈ 547 $/an)** |

## 4. Scénario B — "Cloud-natif" (axe 2 remplacé par un vrai serverless managé)

Même architecture, mais l'axe 2 est confié à AWS Lambda (le fournisseur
gère le cycle de vie éphémère nativement, sans cluster à maintenir) —
hypothèse de volumétrie réaliste pour un projet pédagogique/démo :
**100 000 invocations/mois, 200 ms de durée moyenne, 128 Mo de mémoire**.

Calcul : 100 000 requêtes/mois (sous le quota gratuit de 1M) ;
Go-secondes = 100 000 × 0,2 s × 0,125 Go = **2 500 Go-s/mois**, très
largement sous le quota gratuit de 400 000 Go-s/mois.

| Poste | Dimensionnement | Coût mensuel |
|---|---|---|
| Axe 3 (gateway + Keycloak + target-server) | t3.small | **15,18 $** |
| Axe 2 (AWS Lambda, 100k invocations/mois) | Entièrement sous quota gratuit | **0,00 $** |
| **Total Scénario B** | | **15,18 $/mois (≈ 182 $/an)** |

Le volume devrait dépasser **~2 millions d'invocations/mois à 200 ms/128 Mo**
avant de sortir du quota gratuit Lambda (400 000 Go-s ÷ 0,025 Go-s par
invocation) — très au-dessus de l'usage réaliste d'un capstone académique.

## 5. Synthèse

| | Coût actuel (local) | Scénario A (cloud, as-is) | Scénario B (cloud, optimisé) |
|---|---|---|---|
| **Coût mensuel** | 0 $ (VM étudiante gratuite, B.6) | 45,55 $ | 15,18 $ |
| **Coût annuel** | 0 $ | ≈ 547 $ | ≈ 182 $ |

**Conclusion chiffrée** : migrer l'axe serverless d'un cluster k3s
auto-hébergé vers un service managé (AWS Lambda) réduirait le coût cloud
projeté de **~67 % (-365 $/an)** pour ce projet, car le socle Kubernetes
représente 98,8 % de la charge mesurée pour une fonction qui, en usage
réel pédagogique, reste largement dans le quota gratuit d'un serverless
managé. Le durcissement gVisor de l'axe 1, lui, ne change pas le
dimensionnement de l'instance (le surcoût mesuré de +0,064 vCPU / +28 MiB
tient dans la marge déjà prévue) : la sécurité supplémentaire qu'il
apporte est donc obtenue **à coût cloud nul** dans ce dimensionnement.

## Limites et hypothèses assumées

- Le coût actuel réel payé par le groupe est 0 $ (infrastructure locale
  gratuite, conforme à B.6) ; les scénarios A et B sont des **projections**
  de déploiement en production, pas une dépense engagée.
- La volumétrie Lambda (100 000 invocations/mois) est une hypothèse
  pédagogique raisonnable, explicitée pour rester vérifiable — elle n'est
  pas mesurée en production réelle (le projet n'étant pas déployé).
- Tarifs du 2026-10-03, région eu-west-1 pour t3.micro et us-east-1 pour
  t3.small/t3.medium (les prix eu-west-1 pour ces deux derniers sont
  généralement 5 à 10 % plus élevés qu'us-east-1 chez AWS, non chiffrés
  précisément ici faute de source directe consultée).
- Coût de stockage (images Docker, ~1,5 Go cumulés) non inclus : à l'échelle
  mesurée, un volume EBS gp3 de 20 Go (~0,08 $/Go/mois) ajouterait environ
  1,60 $/mois, négligeable face aux postes compute ci-dessus.
