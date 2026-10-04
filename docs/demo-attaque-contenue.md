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

## Complément : preuve de l'exposition réelle au noyau hôte (2026-10-04)

### Pourquoi ce complément

La formulation du cahier des charges ("compromission totale du système
hôte", B.2) a soulevé une question légitime : nos tests précédents
prouvent une compromission **du conteneur** (root à l'intérieur, lecture
de `/etc/passwd` du conteneur, capacités Linux actives) — jamais un accès
réel à la VM hôte elle-même. C'est un point important à clarifier : par
défaut, même sans gVisor, Docker isole déjà nativement le système de
fichiers et les processus de l'hôte via les namespaces Linux. Obtenir
`root` dans le conteneur ne donne donc pas, en soi, un accès à la VM —
une évasion réelle demanderait une faille noyau exploitable ou une
mauvaise configuration explicite (mode `privileged`, montage du
filesystem hôte), qu'aucun des deux composes de ce projet ne configure
volontairement.

### Ce que gVisor protège réellement

gVisor n'ajoute pas d'isolation filesystem/réseau — Docker la fournit déjà
par défaut. Sa valeur ajoutée est de protéger contre une **faille noyau
non corrigée** qui permettrait de s'évader du conteneur malgré cette
isolation par défaut. Reproduire un exploit d'évasion réel n'est ni sûr
(risque de planter la VM) ni réalisable (un noyau à jour n'a pas de faille
connue à exploiter) — mais on peut prouver, sans danger, que le vecteur
d'attaque que gVisor neutralise existe bel et bien dans le cas standard.

### Protocole et résultat

```bash
docker exec mcp-vulnerable-server-UNSAFE sh -c "cat /proc/version"
docker exec mcp-vulnerable-server-HARDENED sh -c "cat /proc/version"
cat /proc/version   # sur la VM hote, pour comparaison
```

| | Noyau vu depuis l'intérieur |
|---|---|
| VM hôte (réelle) | `Linux ... 7.0.0-34-generic ... Fri Sep 4 2026` |
| Conteneur standard (sans protection) | `Linux ... 7.0.0-34-generic ... Fri Sep 4 2026` — **identique à l'hôte** |
| Conteneur gVisor (durci) | `Linux ... 4.19.0-gvisor #1 SMP Sun Jan 10 2016` — **noyau entièrement émulé, sans rapport avec l'hôte** |

### Interprétation

Le conteneur standard expose le **vrai noyau** de la VM : tout appel
système qu'un attaquant y exécute atteint directement ce noyau réel, donc
toute vulnérabilité noyau existante sur cette version précise serait
exploitable depuis l'intérieur du conteneur — c'est le vecteur d'évasion
que la littérature de sécurité documente (ex. CVE-2019-5736 sur `runc`).
Le conteneur gVisor, lui, ne communique jamais avec ce noyau réel : le
"Sentry" intercepte et répond à chaque appel système dans son propre
espace utilisateur, présentant une identité de noyau totalement fictive.
Même face à une faille 0-day du noyau réel de l'hôte, un attaquant dans
le conteneur gVisor ne pourrait jamais l'atteindre — ses appels système
ne sortent jamais du bac à sable Sentry.

### Conclusion sur la portée exacte de la démonstration

"Compromission totale" dans ce projet désigne un contrôle applicatif
complet du service exposé (exécution de code arbitraire, lecture des
fichiers du conteneur, persistance), pas un accès prouvé à la VM hôte —
cette dernière nécessiterait une faille noyau réelle, hors du périmètre
raisonnable d'un projet académique. Ce que la plateforme démontre, avec
preuve technique directe et sans risque, c'est que le **vecteur** par
lequel une telle évasion serait possible (l'exposition du vrai noyau de
l'hôte) existe dans le cas standard et est **structurellement éliminé**
par gVisor, indépendamment de toute faille noyau spécifique.

### Confirmation complémentaire via MCP Inspector (test direct par le vecteur d'attaque)

Le test précédent utilisait `docker exec`, c'est-à-dire un accès direct au conteneur que
l'attaquant n'a jamais dans un scénario réel. Pour une preuve plus rigoureuse, le même
contrôle a été reproduit **exclusivement via la vulnérabilité `ping_host` elle-même**,
en utilisant l'interface MCP Inspector (sans aucune commande terminal sur les conteneurs).

**Protocole** :
1. Connexion d'Inspector au serveur vulnérable sans protection (`http://127.0.0.1:8001/mcp`)
2. Appel de l'outil `ping_host` avec le payload d'injection : `127.0.0.1; cat /proc/version`
3. Répétition de la même opération sur le serveur durci avec gVisor (`http://127.0.0.1:8002/mcp`)

**Résultats obtenus (captures Inspector, 2026-10-04)** :

| Serveur | Noyau retourné par l'injection |
|---|---|
| Port 8001 (sans protection) | `Linux version 7.0.0-34-generic (buildd@lcy02-amd64-117) ... #34~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC Fri Sep 4 15:38:29 UTC 2` |
| Port 8002 (durci, gVisor) | `Linux version 4.19.0-gvisor #1 SMP Sun Jan 10 15:06:54 PST 2016` |

**Interprétation** : ce test est plus probant que le précédent car il prouve la fuite
d'information *par le chemin d'exploitation réel qu'emprunterait un attaquant* — et non
par un accès privilégié (`docker exec`) que cet attaquant n'aurait jamais. Sur le serveur
non protégé, l'injection de commande donne un accès en lecture au vrai noyau de la machine
hôte (identique à `uname -a` exécuté sur la VM elle-même). Sur le serveur durci, la même
injection, exécutée avec les mêmes droits applicatifs, ne retourne que l'identité fictive
construite par le Sentry gVisor — confirmant qu'aucune fuite d'information noyau réelle
n'est possible même si l'attaquant exploite la faille avec succès.
