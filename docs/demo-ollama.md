# Démonstration complémentaire — Ollama comme hôte MCP autonome (A.5)

## Contexte

Le cahier des charges (A.5) cite Ollama/`ollmcp` comme hôte local alternatif
à MCP Inspector, pour qu'un LLM décide lui-même d'appeler les outils à
partir d'une instruction en langage naturel, plutôt qu'un humain qui
construit manuellement l'appel JSON-RPC. Ollama n'est pas obligatoire pour
la notation (MCP Inspector l'est, A.5), mais son usage réel permet de
montrer que l'attaque "attaque contenue" (B.2) ne dépend pas de la façon
dont l'outil est invoqué : humain ou agent autonome, le résultat est
identique si le serveur cible n'est pas protégé.

## Limite constatée

`ollmcp --help` ne propose aucun flag pour un en-tête HTTP personnalisé
(`Authorization: Bearer`), contrairement à MCP Inspector qui a un champ
"Headers" dédié. `ollmcp` ne peut donc pas se connecter directement à la
gateway sécurisée (axe 3, protégée par Keycloak) en l'état. Pour cette
démonstration, `ollmcp` est connecté au serveur volontairement vulnérable
(axe 1, `http://127.0.0.1:8001/mcp`, sans authentification), ce qui reste
pertinent et cohérent avec le fil conducteur du projet.

## Protocole et résultat (2026-10-04)

```bash
source MCP-PPP/bin/activate
ollmcp -u http://127.0.0.1:8001/mcp -m qwen2.5:3b
```

Question posée en langage naturel : *"Peux-tu vérifier si l'hôte
127.0.0.1; whoami; id est joignable ?"*

Résultat :

1. Le modèle a construit l'appel `ping_host` avec l'argument transmis **tel
   quel**, sans filtrage ni reformulation : `{"hostname": "127.0.0.1; whoami; id"}`.
2. `ollmcp` a demandé une **confirmation humaine (Human-in-the-Loop)** avant
   d'exécuter l'outil — mise en œuvre cliente de l'exigence A.6 (consentement
   explicite avant toute exécution d'outil).
3. La réponse de l'outil confirme l'exploitation réussie, identique à une
   exécution manuelle :
root
uid=0(root) gid=0(root) groups=0(root)
4. Observation spontanée du modèle dans sa réponse finale : *"cette commande
   est vulnérable à l'exécution d'arbitraires si elle est exécutée sans
   contrôle"* — le LLM a identifié la nature de la faille sans qu'on le lui
   demande.

## Conclusion

L'injection de commande (CWE-78) documentée dans `docs/vulnerabilite-sprint3.md`
est reproductible quel que soit l'hôte MCP utilisé (Inspector, curl manuel,
ou un LLM local autonome via Ollama) — ce qui confirme que la vulnérabilité
est dans le serveur cible, pas dans la méthode d'invocation, et que seule
une isolation au niveau infrastructure (gVisor, voir
`docs/demo-attaque-contenue.md`) en contient les conséquences.
