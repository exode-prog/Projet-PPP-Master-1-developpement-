#!/bin/bash
set -e

KC_URL="${KC_URL:-http://localhost:8080}"
ADMIN_USER="${KC_ADMIN_USER:-admin}"
ADMIN_PASS="${KC_ADMIN_PASSWORD:-admin}"
REALM="mcp-secure-platform"
CLIENT_ID="mcp-target-server"
CLIENT_SECRET="${MCP_CLIENT_SECRET:-R48PxLtdsncHJ19VcOpXxvQ0qVF0mChttVFpjJFBRmxVd1BE1fQQF9gEnbdjUjeSi1i6qAieNUCdv2BNxCBdeY}"
ROLE_NAME="mcp-user"
TEST_USER="testuser"
TEST_PASS="test1234"

KCADM="/opt/keycloak/bin/kcadm.sh"

echo "Attente de Keycloak et connexion admin sur $KC_URL ..."
until $KCADM config credentials --server "$KC_URL" --realm master --user "$ADMIN_USER" --password "$ADMIN_PASS" 2>/dev/null; do
  sleep 2
done
echo "Keycloak pret, connexion admin etablie."

if ! $KCADM get realms/$REALM >/dev/null 2>&1; then
  echo "Creation du royaume $REALM"
  $KCADM create realms -s realm=$REALM -s enabled=true
else
  echo "Royaume $REALM deja present, on ne touche a rien"
fi

CLIENT_UUID=$($KCADM get clients -r $REALM -q clientId=$CLIENT_ID | grep -o '"id" : "[^"]*"' | head -1 | sed 's/"id" : "//;s/"$//')
if [ -z "$CLIENT_UUID" ]; then
  echo "Creation du client $CLIENT_ID"
  $KCADM create clients -r $REALM \
    -s clientId=$CLIENT_ID \
    -s enabled=true \
    -s publicClient=false \
    -s secret=$CLIENT_SECRET \
    -s directAccessGrantsEnabled=true \
    -s standardFlowEnabled=true
else
  echo "Client $CLIENT_ID deja present (id=$CLIENT_UUID), on ne touche a rien"
fi

if ! $KCADM get roles/$ROLE_NAME -r $REALM >/dev/null 2>&1; then
  echo "Creation du role $ROLE_NAME"
  $KCADM create roles -r $REALM -s name=$ROLE_NAME
else
  echo "Role $ROLE_NAME deja present"
fi

USER_ID=$($KCADM get users -r $REALM -q username=$TEST_USER | grep -o '"id" : "[^"]*"' | head -1 | sed 's/"id" : "//;s/"$//')
if [ -z "$USER_ID" ]; then
  echo "Creation de l'utilisateur $TEST_USER"
  $KCADM create users -r $REALM -s username=$TEST_USER -s enabled=true -s email=$TEST_USER@example.com -s emailVerified=true -s firstName=Test -s lastName=User
else
  echo "Utilisateur $TEST_USER deja present (id=$USER_ID), on ne recree pas"
fi

echo "Fixation/verification du mot de passe de $TEST_USER"
$KCADM set-password -r $REALM --username $TEST_USER --new-password $TEST_PASS

echo "Suppression des actions requises par defaut (verification email, etc.)"
$KCADM update users/$USER_ID -r $REALM -s 'requiredActions=[]' 2>/dev/null || true

echo "Attribution du role $ROLE_NAME a $TEST_USER (sans erreur si deja attribue)"
$KCADM add-roles -r $REALM --uusername $TEST_USER --rolename $ROLE_NAME 2>/dev/null || echo "(deja attribue ou non applicable, on continue)"

# --- RBAC : second role + second utilisateur (pour demontrer le refus d'acces) ---
ADMIN_ROLE_NAME="mcp-admin"
ADMIN_USER="adminuser"
ADMIN_PASS="admin1234"

if ! $KCADM get roles/$ADMIN_ROLE_NAME -r $REALM >/dev/null 2>&1; then
  echo "Creation du role $ADMIN_ROLE_NAME"
  $KCADM create roles -r $REALM -s name=$ADMIN_ROLE_NAME
else
  echo "Role $ADMIN_ROLE_NAME deja present"
fi

ADMIN_USER_ID=$($KCADM get users -r $REALM -q username=$ADMIN_USER | grep -o '"id" : "[^"]*"' | head -1 | sed 's/"id" : "//;s/"$//')
if [ -z "$ADMIN_USER_ID" ]; then
  echo "Creation de l'utilisateur $ADMIN_USER"
  $KCADM create users -r $REALM -s username=$ADMIN_USER -s enabled=true -s email=$ADMIN_USER@example.com -s emailVerified=true -s firstName=Admin -s lastName=User
  ADMIN_USER_ID=$($KCADM get users -r $REALM -q username=$ADMIN_USER | grep -o '"id" : "[^"]*"' | head -1 | sed 's/"id" : "//;s/"$//')
else
  echo "Utilisateur $ADMIN_USER deja present (id=$ADMIN_USER_ID), on ne recree pas"
fi

echo "Fixation/verification du mot de passe de $ADMIN_USER"
$KCADM set-password -r $REALM --username $ADMIN_USER --new-password $ADMIN_PASS
$KCADM update users/$ADMIN_USER_ID -r $REALM -s 'requiredActions=[]' 2>/dev/null || true

echo "Attribution des roles a $ADMIN_USER (mcp-user + mcp-admin)"
$KCADM add-roles -r $REALM --uusername $ADMIN_USER --rolename $ROLE_NAME 2>/dev/null || echo "(deja attribue, on continue)"
$KCADM add-roles -r $REALM --uusername $ADMIN_USER --rolename $ADMIN_ROLE_NAME 2>/dev/null || echo "(deja attribue, on continue)"

echo "Initialisation Keycloak terminee avec succes."
