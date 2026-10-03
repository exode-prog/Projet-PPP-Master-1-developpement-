# Étude comparative : gVisor vs Firecracker

## Contexte

Le cahier des charges (Partie B.3, Axe 1) demande une étude comparative avec les microVMs Firecracker, en complément de l'implémentation gVisor retenue pour ce projet. Ce document analyse les deux approches d'isolation runtime pour justifier le choix technique effectué.

## Deux philosophies d'isolation différentes

### gVisor — Noyau applicatif en espace utilisateur

gVisor s'interpose entre le conteneur et le noyau Linux réel via un composant nommé **Sentry**, un noyau réimplémenté en espace utilisateur (userspace). Chaque appel système émis par le conteneur est intercepté, analysé, puis soit simulé directement par Sentry, soit transmis de façon très restreinte au vrai noyau.

Le conteneur continue de s'exécuter comme un processus Linux classique côté hôte, mais ne "voit" jamais directement le véritable noyau.

### Firecracker — Micro-machine virtuelle (microVM)

Firecracker, développé par AWS, crée une **véritable machine virtuelle légère**, avec son propre noyau Linux minimal, isolée par les mécanismes de virtualisation matérielle (KVM). Chaque charge de travail tourne dans sa propre microVM, complètement séparée du noyau hôte au niveau matériel, pas seulement logiciel.

C'est la technologie qui fait fonctionner AWS Lambda et AWS Fargate à grande échelle.

## Tableau comparatif

| Critère | gVisor | Firecracker |
|---|---|---|
| Mécanisme d'isolation | Interception des appels système (userspace kernel) | Virtualisation matérielle (KVM) |
| Niveau d'isolation | Fort, mais partage in fine le noyau hôte pour certaines opérations | Maximal : isolation au niveau matériel, noyau dédié par instance |
| Temps de démarrage | Quasi instantané (overhead minime sur un conteneur classique) | Très rapide (~125 ms), mais supérieur à un simple conteneur |
| Complexité de déploiement | Faible : s'intègre directement comme runtime Docker alternatif (`--runtime=runsc`) | Élevée : nécessite KVM, configuration réseau dédiée (TAP devices), images noyau et rootfs spécifiques |
| Compatibilité applicative | Très bonne pour la majorité des appels système standards ; certains appels rares peuvent ne pas être supportés | Totale : un vrai noyau Linux complet tourne dans la microVM |
| Overhead de performance | Léger surcoût sur les appels système fréquents (I/O intensif) | Overhead de virtualisation, mais optimisé pour un démarrage rapide |
| Cas d'usage typique | Renforcement de conteneurs existants sans changer l'architecture (Google Cloud Run, GKE Sandbox) | Isolation multi-tenant à très grande échelle pour du serverless (AWS Lambda, Fargate) |
| Intégration Docker | Native via runtime alternatif | Nécessite un orchestrateur dédié (Firecracker n'est pas un runtime OCI direct) |

## Mesures réelles effectuées sur ce projet (2026-10-03)

Le tableau ci-dessus synthétise des caractéristiques générales de l'industrie (gVisor vs Firecracker). En complément, une mesure empirique réelle a été effectuée sur ce projet, comparant le serveur vulnérable du Sprint 3 exécuté en conteneur standard (`docker-compose.vulnerable.yml`) et sa version durcie sous gVisor (`docker-compose.vulnerable-hardened.yml`) — protocole et preuves complètes dans `docs/demo-attaque-contenue.md` :

| Indicateur | Conteneur standard | Conteneur gVisor (`runsc`) |
|---|---|---|
| Cold-start | 6,43 s | 7,31 s (+14 %) |
| CPU à l'idle | 0,37 % | 6,77 % |
| RAM à l'idle | 64,22 MiB | 92,19 MiB |

Firecracker n'ayant jamais été installé dans ce projet (voir justification ci-dessous), aucune troisième colonne mesurée n'est présentée : plutôt que d'inventer des chiffres non vérifiés, cette limitation est assumée explicitement, et la comparaison avec Firecracker reste fondée sur des valeurs de référence publiques (notamment son temps de démarrage ~125 ms, largement documenté par AWS).

## Pourquoi gVisor a été retenu pour ce projet

1. **Intégration immédiate avec Docker** : gVisor s'active simplement avec `--runtime=runsc` ou `runtime: runsc` dans un docker-compose, sans reconfiguration profonde de l'infrastructure existante (validé aux Sprints 1 à 3 de ce projet).

2. **Complexité de mise en œuvre adaptée au contexte académique** : Firecracker nécessite une configuration réseau et système bien plus lourde (accès KVM, TAP devices, images kernel/rootfs dédiées), difficilement réalisable dans le temps imparti d'un sprint sur une VM de développement standard.

3. **Niveau de protection suffisant pour la démonstration visée** : comme démontré au Sprint 4 (Tâche 4), gVisor confine efficacement l'attaquant à l'intérieur du conteneur, empêchant toute atteinte au système hôte réel — l'objectif du scénario "attaque contenue" est pleinement atteint.

4. **Cohérence avec l'écosystème du projet** : gVisor s'intègre nativement dans le flux Docker déjà utilisé pour l'ensemble du projet (Sprint 1 à 3), alors que Firecracker demanderait une architecture parallèle distincte.

## Quand Firecracker serait le choix préférable

Dans un contexte de production à très grande échelle (plateforme serverless multi-tenant, isolation de charges de travail totalement inconnues et non fiables, exigence réglementaire d'isolation matérielle stricte), Firecracker offrirait une garantie de sécurité supérieure, au prix d'une complexité opérationnelle largement accrue. C'est un choix pertinent pour un axe futur d'évolution du projet (Sprint 5, architecture serverless), où l'utilisation de LocalStack permettra d'explorer cette piste de façon complémentaire.

## Conclusion

gVisor représente le meilleur compromis entre niveau d'isolation, simplicité d'intégration et faisabilité dans le cadre de ce projet académique. La démonstration du Sprint 4 (Tâche 4) valide empiriquement que ce niveau de protection est suffisant pour contenir l'attaque testée, tout en restant réalisable avec les ressources et le temps disponibles.
