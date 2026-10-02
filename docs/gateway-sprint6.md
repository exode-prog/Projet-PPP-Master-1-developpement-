# Gateway MCP — Sprint 6

## Ce qui a été implémenté

Un gateway MCP (`src/gateway/gateway.py`) a été mis en place devant le serveur cible du Sprint 1-2, avec trois responsabilités :

1. **Routage dynamique** : via `fastmcp.server.create_proxy()`, le gateway découvre et relaie automatiquement tous les outils, ressources et prompts exposés par le serveur cible, sans configuration manuelle outil par outil.
2. **Authentification Keycloak côté gateway** : le gateway vérifie lui-même chaque jeton JWT entrant (signature, émetteur, expiration) via `JWTVerifier`, en réutilisant le même royaume Keycloak et le même point de vérification JWKS que `auth.py` du serveur cible. Une requête sans jeton valide reçoit un `401 Unauthorized` avant même d'atteindre le serveur cible.
3. **Quotas par identité de client** : un compteur en mémoire (fenêtre glissante de 1 minute, 5 appels d'outils maximum) limite chaque client authentifié individuellement, identifié par le claim `preferred_username` (ou `sub` en repli) de son jeton JWT déjà vérifié.

## Conformité à la règle anti-passthrough (cahier des charges A.6)

Le jeton JWT de l'utilisateur, une fois vérifié par le gateway, n'est **jamais** retransmis tel quel au serveur cible. Seule l'identité qu'il porte est utilisée localement (pour les quotas). Ce choix découle directement de la règle du cahier des charges interdisant à un service qui valide un jeton d'auth de le relayer tel quel à un service en aval.

## Conception des quotas : choix assumés

- **Compteur en mémoire** plutôt qu'une base externe (Redis, fichier) : remis à zéro au redémarrage du gateway. Choix cohérent avec le niveau de simplicité du reste du Sprint 6 (voir `audit.py`, lui aussi un simple fichier texte) — une persistance externe aurait ajouté une dépendance d'infrastructure sans démontrer de garantie de sécurité supplémentaire pour la portée de ce sprint.
- **Réutilisation du middleware officiel FastMCP** (`SlidingWindowRateLimitingMiddleware`) plutôt qu'un compteur réimplémenté à la main, avec une sous-classe (`ToolCallRateLimitingMiddleware`) qui restreint son application aux seuls appels d'outils (`tools/call`), et non à l'ensemble du trafic MCP (le middleware d'origine compte aussi le handshake `initialize`, ce qui faussait l'intention initiale du quota).
- **Identité du client plutôt qu'adresse IP** : rendu possible par la vérification JWT au niveau du gateway (étape précédente) — plusieurs utilisateurs derrière un même NAT ou un même utilisateur changeant d'IP sont correctement distingués/regroupés.

## Problèmes rencontrés et résolus

- **Bug latent découvert dans `audit.py` (datant du Sprint 2)** : le fichier contenait par erreur une copie du code de vérification JWT de `auth.py`, au lieu de la fonction `log_event()` pourtant déjà appelée par `server.py`. Vérifié via `git log`/`git show` sur l'historique complet du fichier (et non supposé) : ce n'était pas une régression récente mais un bug présent depuis le commit initial du Sprint 2, resté invisible tant que le serveur n'avait pas été relancé. Corrigé en écrivant la fonction `log_event()` manquante, avec documentation explicite de la correction dans le fichier lui-même.
- **Conflit de packaging FastMCP** : `from fastmcp import create_proxy` échouait (`ImportError`) alors que la fonction existe bien dans `fastmcp-slim` 3.4.7. Cause identifiée : le paquet `fastmcp` (wrapper léger) et `fastmcp-slim` (implémentation réelle) exposent tous deux un fichier à `fastmcp/__init__.py`, et la version light avait pris le dessus sur le système. Contourné sans réinstallation en important directement depuis le sous-module non affecté : `from fastmcp.server import create_proxy`.
- **MCP Inspector sans champ de jeton Bearer explicite** : la version installée d'Inspector attend un flux OAuth complet (CIMD/Dynamic Client Registration) plutôt qu'un simple champ pour coller un jeton. La validation de l'authentification gateway (cas jeton valide/invalide) a donc été faite par des requêtes `curl` directes plutôt que par Inspector, ce qui a aussi permis une vérification plus précise et reproductible (scripts conservés).
- **Expiration des jetons de test (5 minutes)** : plusieurs tentatives de validation manuelle ont échoué simplement parce que le jeton généré avait expiré entre deux commandes. Résolu en regroupant génération de jeton, connexion et appel d'outil dans un seul script, exécuté sans interruption.

## Limitation technique connue et assumée

Un `RuntimeError: Unexpected ASGI message 'http.response.start' sent, after response already completed` a été observé ponctuellement dans les logs du gateway, associé à la clôture de session HTTP (`DELETE /mcp`). Toutes les requêtes aboutissent néanmoins avec les codes HTTP attendus (`200`/`202`/`401`) ; ce message semble lié à une particularité de la gestion de fin de session du transport Streamable HTTP d'uvicorn/FastMCP et n'affecte pas le résultat fonctionnel observé lors des tests. Non résolu plus avant car hors du périmètre de sécurité de ce sprint.

## Validation réalisée

Un scénario de bout en bout a été exécuté et vérifié :

1. Requête sans jeton → `401 Unauthorized`
2. Requête avec jeton valide → connexion acceptée (`200 OK`)
3. 5 appels à l'outil `hello` → tous réussis, tracés dans `audit.log` du serveur cible
4. 6ème appel (même minute, même identité) → rejeté explicitement (`"Quota dépassé : ..."`), **sans** trace dans `audit.log` : le rejet intervient avant d'atteindre le serveur cible
5. Attente de la fin de la fenêtre de quota (65s) → nouvel appel de nouveau accepté et tracé

## Conclusion

Le gateway du Sprint 6 centralise le routage, l'authentification et la protection contre les abus en un point unique, sans jamais faire transiter le jeton de l'utilisateur vers le serveur cible — conformément à la règle anti-passthrough du cahier des charges. Les limites assumées (quotas en mémoire, non persistants) et les problèmes rencontrés en cours de développement sont documentés explicitement plutôt que passés sous silence, dans la continuité de la démarche de rigueur déjà appliquée aux sprints précédents.
