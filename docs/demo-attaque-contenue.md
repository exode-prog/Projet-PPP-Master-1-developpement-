# Démonstration « Attaque contenue » — validation empirique (Sprint 3/4)

## Contexte

La fiche `docs/vulnerabilite-sprint3.md` documentait la vulnérabilité (CWE-78, injection de commande dans l'outil `ping_host`) mais sa checklist restait partiellement non cochée, faute de preuve conservée d'une exécution réelle du scénario comparatif. Ce document capture une exécution complète et rejouable, avec preuves à l'appui, conformément à la carte Trello « Scénario attaque contenue complet » et au fil conducteur du cahier des charges (Partie B.2).

## Protocole

Scénario rejoué d'un seul tenant (`docker compose build` puis `up`, exploitation via l'outil MCP `ping_host`, puis arrêt complet), successivement sur :

1. `docker-compose.vulnerable.yml` — serveur SANS aucune protection (baseline Sprint 3)
2. `docker-compose.vulnerable-hardened.yml` — même code applicatif, exécuté sous `runtime: runsc` (gVisor) avec `cap_drop: ALL`, `read_only: true`, `tmpfs: /tmp:noexec,nosuid` et `no-new-privileges:true` (durcissement Sprint 4)

Pour chaque version : mesure du cold-start (temps entre le lancement du conteneur et sa disponibilité réseau), relevé `docker stats` à l'idle, puis cinq tentatives d'exploitation identiques via le payload d'injection `hostname`.

## Résultats mesurés (exécution du 2026-10-03)

| Indicateur | Sans protection | Durci gVisor |
|---|---|---|
| Cold-start | 6,43 s | 7,31 s (**+14 %**) |
| CPU à l'idle | 0,37 % | 6,77 % |
| RAM à l'idle | 64,22 MiB | 92,19 MiB |
| Processus (PIDs) | 1 | 29 (overhead du Sentry gVisor) |
| `CapEff` (capacités Linux effectives) | `00000000a80425fb` | `0000000000000000` |
| Lecture de `/etc/passwd` | ✅ réussie | ✅ réussie (lecture seule non bloquée) |
| Écriture arbitraire hors `/tmp` (`/app/pwned.txt`) | ✅ réussie | ❌ `Read-only file system` |
| Création + exécution d'un script dans `/tmp` | ✅ réussie | ❌ `Permission denied` (montage `noexec`) |

## Interprétation

La vulnérabilité applicative (injection de commande) **reste exploitable dans les deux cas** — conforme au choix assumé du projet : ce n'est pas le code qui est corrigé, mais l'infrastructure qui contient les conséquences de son exploitation (voir `docs/vulnerabilite-sprint3.md`, section Remédiation).

La différence se joue entièrement sur ce qu'un attaquant peut faire **après** l'injection initiale :

- **Sans protection** : capacités Linux root complètes (`CapEff` non nul), persistance totale possible (écriture puis exécution d'un script arbitraire).
- **Avec gVisor + durcissement** : capacités totalement supprimées, toute tentative de persistance échoue immédiatement, que ce soit par écriture (système de fichiers racine en lecture seule) ou par exécution depuis la seule zone inscriptible (`/tmp` monté `noexec`).

Le surcoût mesuré (cold-start +14 %, RAM +28 MiB, CPU idle +6,4 points, nombre de processus multiplié par ~29 du fait de l'architecture Sentry de gVisor) est le prix de ce confinement — cohérent avec le compromis "sécurité contre overhead" déjà discuté de façon théorique dans `docs/comparatif-gvisor-firecracker.md`, ici quantifié sur ce projet précis plutôt que sur des chiffres de littérature.

## Conclusion

Le scénario "attaque contenue" du cahier des charges (B.2) est validé empiriquement, avec preuves capturées et chiffrées. La checklist de `docs/vulnerabilite-sprint3.md` est mise à jour en conséquence, en référence à ce document.
