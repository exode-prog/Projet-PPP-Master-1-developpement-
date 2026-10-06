# Fiche de vulnérabilité — Sprint 3

## Identification

- **Composant concerné** : `src/vulnerable_server/server.py`
- **Tool affecté** : `ping_host`
- **Type de vulnérabilité** : Injection de commande OS (OS Command Injection)
- **Référence** : CWE-78
- **Sévérité** : Critique (exécution de code arbitraire avec les droits du processus serveur)

## Description

Le Tool `ping_host` construit une commande shell en concaténant directement le paramètre `hostname`, fourni par l'utilisateur, sans validation ni échappement :

```python
command = f"ping -c 1 {hostname}"
result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
```

L'utilisation de `shell=True` combinée à une concaténation directe permet à un attaquant d'injecter des métacaractères interprétés par le shell (`;`, `&&`, `|`, `` ` ``, `$()`), transformant une commande `ping` légitime en une chaîne de commandes arbitraires.

## Vecteur d'attaque

Un attaquant contrôlant le paramètre `hostname` (via un appel direct au Tool MCP, ou via un LLM manipulé par une injection de prompt) peut faire exécuter n'importe quelle commande système.

## Preuve de concept (PoC)

| Entrée fournie (`hostname`) | Commande réellement exécutée | Effet |
|---|---|---|
| `127.0.0.1; whoami` | `ping -c 1 127.0.0.1; whoami` | Révèle l'utilisateur système exécutant le serveur |
| `127.0.0.1 && cat /etc/passwd` | `ping -c 1 127.0.0.1 && cat /etc/passwd` | Lecture d'un fichier système sensible |
| `$(id)` | `ping -c 1 $(id)` | Exécution de commande imbriquée |
| `127.0.0.1; rm -rf /tmp/test` | `ping -c 1 127.0.0.1; rm -rf /tmp/test` | Suppression de fichiers (destructif) |

## Impact

- **Confidentialité** : lecture de fichiers arbitraires accessibles à l'utilisateur du processus
- **Intégrité** : modification ou suppression de fichiers
- **Disponibilité** : possibilité de commandes destructives ou de déni de service
- **Portée** : limitée aux droits du processus Python exécutant le serveur (d'où l'intérêt du principe de moindre privilège déjà appliqué via l'utilisateur non-root dans le Dockerfile)

## Remédiation

### Corrective (bonne pratique standard, non appliquée ici volontairement)
Utiliser `subprocess.run(["ping", "-c", "1", hostname], shell=False)` avec une liste d'arguments plutôt qu'une chaîne shell, et valider `hostname` avec une expression régulière stricte.

### Approche retenue dans ce projet (Sprint 4)
Plutôt que de corriger le code, ce projet démontre une **isolation au niveau infrastructure** : même si la vulnérabilité applicative reste présente, l'exécution du serveur dans un environnement sandboxé (gVisor, seccomp, AppArmor, isolation réseau) doit empêcher l'attaquant d'atteindre le système hôte réel, quelle que soit la commande injectée.

**Précision importante (testée empiriquement)** : sous `runtime: runsc` (gVisor), les profils seccomp et AppArmor personnalisés déclarés via `security_opt` ne sont **pas évalués par le noyau hôte** — gVisor intercepte les appels système dans son propre espace utilisateur (le Sentry) avant qu'ils n'atteignent les hooks seccomp/LSM classiques. Vérifié par l'absence totale d'entrées `apparmor="DENIED"` dans les logs noyau pour le conteneur durci, malgré un accès réussi à `/etc/shadow` lors d'un test volontaire. Les deux profils personnalisés ont donc été validés séparément sous le runtime standard (`runc`, voir `docker-compose.vulnerable-seccomp-apparmor-test.yml`) où ils bloquent effectivement `ptrace`, `mount` et l'accès à `/etc/shadow` (confirmé par les logs noyau). Sous gVisor, l'isolation effective repose donc principalement sur gVisor lui-même (CapEff=0, noyau virtualisé séparé) ; seccomp/AppArmor restent déclarés en défense en profondeur mais sont redondants avec les garanties déjà apportées par le Sentry.

## Statut

- [x] Vulnérabilité implémentée (Sprint 3)
- [x] Exploitation testée sans protection (Sprint 3, Tâche 3)
- [x] Neutralisation validée avec gVisor (Sprint 4)
- [x] Profil seccomp personnalisé écrit et validé (Sprint 4) — `security/seccomp-hardened.json`
- [x] Profil AppArmor personnalisé écrit et validé (Sprint 4) — `security/apparmor-mcp-vulnerable-hardened.profile`

Preuve complète (cold-start, consommation de ressources, capacités Linux effectives avant/après, tentatives de persistance) : voir `docs/demo-attaque-contenue.md`, rejouée et capturée le 2026-10-03 lors de l'intégration finale du projet.
