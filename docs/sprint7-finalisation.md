# Sprint 7 — Finalisation, intégration et TCO

## Introduction

Après la conteneurisation complète de la gateway (Sprint 6) et la
validation empirique du scénario "attaque contenue" (Sprint 3/4), ce
sprint clôture la partie technique du projet. Son objectif est double :

1. **Vérifier** que les trois axes du cahier des charges (sandbox/gVisor,
   serverless/OpenFaaS, gateway/orchestration) sont réellement
   fonctionnels ensemble, et documenter comment ils s'articulent sans être
   fusionnés (architecture "Option A", choisie dès le Sprint 3 pour des
   raisons de sécurité).
2. **Chiffrer le coût réel** de la plateforme (critère B.8 "Finition,
   GitHub & TCO", 15 % de la note), jamais traité jusqu'ici.

Aucun nouveau composant n'a été développé pendant ce sprint : le travail a
consisté à vérifier l'existant, corriger une régression d'infrastructure,
et produire la documentation de synthèse manquante.

## Étapes réalisées

1. **Inventaire de l'axe 2 (serverless)**, jamais vérifié en détail dans
   cette phase du projet : namespaces k3s (`openfaas`, `openfaas-fn`),
   pods actifs, contenu de `stack.yaml` et `no-egress-policy.yaml`,
   historique git du Sprint 5.
2. **Détection d'une anomalie d'infrastructure** : le conteneur `keycloak`
   était arrêté (`Exited 255`) depuis ~15h, sans trace d'erreur
   applicative dans ses logs ni dans l'historique des commandes — cause
   la plus probable : un redémarrage de la VM ou du démon Docker, les
   autres conteneurs de la stack principale ayant été relancés séparément
   ~3h avant ce diagnostic.
3. **Test fonctionnel réel de la fonction OpenFaaS** : premier essai via
   `127.0.0.1:8080` en échec (mauvais point d'entrée, adresse de
   déploiement et non d'invocation) ; second essai via le NodePort
   `31112` réussi (HTTP 200, réponse JSON cohérente).
4. **Relance de la stack principale** (`docker compose up -d`) :
   Keycloak revenu `Healthy` en 21,9 s.
5. **Nettoyage** : arrêt du serveur volontairement vulnérable, resté actif
   après la démonstration MCP Inspector de la session précédente.
6. **Revalidation complète de l'authentification** : obtention d'un token
   Keycloak réel (`mcp-target-server` / `testuser`), appel `initialize`
   accepté par la gateway (`MCP Gateway - Sprint 6 v4.0.10`).
7. **Vérification croisée code/infrastructure** : recherche de toute
   référence à OpenFaaS dans `src/` (gateway, target-server) — aucune
   trouvée, confirmant que les axes restent indépendants au niveau code,
   conformément au choix architectural du projet.
8. **Rédaction de `docs/integration-3-axes.md`** documentant l'état
   vérifié des trois axes et le choix d'intégration légère.
9. **Calcul du TCO** (`docs/tco.md`) : mesure réelle de la consommation
   CPU/RAM de chaque composant (`docker stats`, `kubectl top`), conversion
   en dimensionnement cloud AWS, chiffrage avec tarifs publics sourcés et
   datés (2026-10-03), comparaison d'un scénario "tel quel" et d'un
   scénario "cloud-natif" optimisé.

## Tableaux comparatifs consolidés

### Axe 1 — Conteneur standard vs gVisor (voir `docs/demo-attaque-contenue.md`)

| Indicateur | Sans protection | Durci gVisor |
|---|---|---|
| Cold-start | 6,43 s | 7,31 s (+14 %) |
| CPU à l'idle | 0,37 % | 6,77 % |
| RAM à l'idle | 64,22 MiB | 92,19 MiB |
| `CapEff` | `00000000a80425fb` | `0000000000000000` |
| Écriture hors `/tmp` | réussie | bloquée (`Read-only file system`) |
| Exécution depuis `/tmp` | réussie | bloquée (`Permission denied`) |

### Axe 2 — Répartition de charge mesurée du nœud k3s

| Composant | CPU | RAM | Part du nœud |
|---|---|---|---|
| Fonction `mcp-server-function` | 9 m | 27 Mi | ~1,2 % |
| Socle Kubernetes (CoreDNS, Traefik, OpenFaaS control-plane...) | 771 m | 4 329 Mi | ~98,8 % |
| **Total nœud** | **780 m (19 %)** | **4 356 Mi (54 %)** | 100 % |

### Axe 3 — État de la stack principale (consommation à l'idle)

| Conteneur | CPU | RAM |
|---|---|---|
| `keycloak` | 7,39 % | 606,2 MiB |
| `mcp-gateway` | 0,28 % | 77,97 MiB |
| `mcp-target-server` | 0,26 % | 85,82 MiB |

### Synthèse TCO (voir `docs/tco.md` pour le détail du calcul)

| | Coût actuel (local) | Scénario A (cloud, as-is) | Scénario B (cloud, optimisé Lambda) |
|---|---|---|---|
| Mensuel | 0 $ | 45,55 $ | 15,18 $ |
| Annuel | 0 $ | ≈ 547 $ | ≈ 182 $ |

### Statut final des trois axes

| Axe | Statut | Preuve |
|---|---|---|
| 1 — Sandbox (gVisor) | ✅ Validé et mesuré | `docs/demo-attaque-contenue.md` |
| 2 — Serverless (OpenFaaS/k3s) | ✅ Fonctionnel, testé en direct | `docs/integration-3-axes.md` |
| 3 — Gateway/orchestration | ✅ Relancé et revérifié bout-en-bout | `docs/gateway-sprint6.md` |

## Conclusion

Les trois axes techniques sont fonctionnels, vérifiés en conditions
réelles, et le coût de la plateforme est désormais chiffré avec des
sources datées. Le projet est prêt pour la rédaction du rapport PDF et du
support de soutenance.
