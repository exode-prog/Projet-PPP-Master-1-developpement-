# ⚠️ Serveur MCP VOLONTAIREMENT VULNÉRABLE ⚠️

**NE JAMAIS DÉPLOYER CE CODE EN DEHORS D'UN ENVIRONNEMENT DE LABORATOIRE ISOLÉ.**

## Contexte

Ce serveur contient une injection de commande (CWE-78) introduite délibérément dans le Tool `ping_host`, à des fins strictement pédagogiques et démonstratives (Sprint 3 du projet PPP).

Objectif : servir de cobaye pour la démonstration "attaque contenue" — ce serveur est attaqué sans protection (Sprint 3), puis le même code est protégé par gVisor et un durcissement système (Sprint 4).

Voir `docs/vulnerabilite-sprint3.md` pour la fiche technique complète de la vulnérabilité.

## Règles d'usage strictes

- Ne jamais exposer ce serveur sur un réseau autre que `127.0.0.1` (localhost strict)
- Ne jamais l'inclure dans le `docker-compose.yml` principal du projet
- Ne jamais le lancer sur une machine connectée à un réseau partagé ou public
- Toujours utiliser le script `run_isolated.sh` pour le lancer, jamais `python server.py` directement
- Ne jamais exécuter les PoC destructifs de la fiche de vulnérabilité (suppression de fichiers)

## Lancement autorisé

```bash
./run_isolated.sh
```

## Arrêt

`Ctrl+C`, ou vérifier qu'aucun processus résiduel ne tourne avec `ps aux | grep vulnerable_server`.
