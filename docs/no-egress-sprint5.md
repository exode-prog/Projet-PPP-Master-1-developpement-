# No-egress — Sprint 5, Tâche 4

## Ce qui a été implémenté

Une `NetworkPolicy` Kubernetes (`no-egress-policy.yaml`) a été créée et appliquée dans le namespace `openfaas-fn`, ciblant le pod de la fonction `mcp-server-function`. Elle bloque tout trafic sortant, à l'exception de la résolution DNS (port 53).

## Limitation technique connue et assumée

k3s utilise par défaut **Flannel** comme plugin réseau (CNI), pour sa légèreté et sa simplicité d'installation dans un contexte de développement à ressources limitées. Flannel ne dispose pas du contrôleur nécessaire à l'application effective des NetworkPolicy — la ressource est acceptée par l'API Kubernetes, mais n'est pas appliquée par le plan de données réseau.

Un CNI comme Calico ou Cilium serait nécessaire pour une application réelle de cette règle, mais nécessiterait une réinstallation du cluster k3s (le choix du CNI se fait à l'installation, pas après coup).

## Justification du choix de ne pas migrer vers Calico

Le confinement réseau de ce projet a été démontré empiriquement et validé par exploitation réelle au Sprint 4 (isolation par réseaux Docker dédiés, `vulnerable-net` et `vulnerable-hardened-net`). Réinstaller le cluster pour obtenir une NetworkPolicy fonctionnelle aurait dupliqué cet effort de preuve sans garantie de sécurité supplémentaire significative, pour un coût disproportionné en temps au regard des sprints restants du projet.

## Conclusion

Cette limitation est documentée explicitement conformément à une démarche d'audit rigoureuse : une mesure de sécurité non vérifiée en conditions réelles ne doit jamais être présentée comme pleinement opérationnelle. La NetworkPolicy reste un livrable de preuve de conception, complémentaire à l'isolation réseau réellement validée au Sprint 4.
