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
  # Bug corrige : CLIENT_UUID n'etait jamais relu apres creation sur un realm
  # neuf, et restait vide pour tout le reste du script (echec silencieux de
  # l'attachement des scopes plus loin, URL .../clients//default-client-scopes/...).
  CLIENT_UUID=$($KCADM get clients -r $REALM -q clientId=$CLIENT_ID | grep -o '"id" : "[^"]*"' | head -1 | sed 's/"id" : "//;s/"$//')
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

# --- Scopes OAuth distincts du RBAC (cahier des charges B.5, Couche 1) ---
# Contrairement aux roles RBAC ci-dessus (mcp-user/mcp-admin, lies a l'IDENTITE
# permanente de l'utilisateur dans Keycloak), un scope OAuth decrit ce que CE
# JETON PRECIS a ete autorise a demander au moment de son emission (parametre
# scope= de la requete de token). Un utilisateur avec le role mcp-admin peut
# tout de meme obtenir un jeton SANS le scope mcp:tools:write, et se voir alors
# refuser l'acces a l'outil "add" malgre son role : les deux controles sont
# volontairement independants.

SCOPE_READ_NAME="mcp:tools:read"
SCOPE_WRITE_NAME="mcp:tools:write"

# NB : l'image quay.io/keycloak/keycloak ne fournit pas python3. On extrait
# les ids a la main (grep/sed), soit directement depuis la sortie de "kcadm
# create" (qui affiche "Created new client-scope with id '...'"), soit en
# cherchant la ligne "id" la plus proche de la ligne "name" correspondante
# dans la liste JSON retournee par "kcadm get client-scopes".

get_scope_id() {
  local scope_name="$1"
  $KCADM get client-scopes -r $REALM 2>/dev/null \
    | grep -B 3 "\"name\" : \"$scope_name\"" \
    | grep -o '"id" : "[^"]*"' \
    | tail -1 \
    | sed 's/"id" : "//;s/"$//'
}

create_scope_if_missing() {
  local scope_name="$1"
  local existing_id
  existing_id=$(get_scope_id "$scope_name")
  if [ -n "$existing_id" ]; then
    echo "$existing_id"
    return
  fi
  cat > /tmp/scope_payload.json <<JSON
{
  "name": "$scope_name",
  "protocol": "openid-connect",
  "attributes": {
    "include.in.token.scope": "true",
    "display.on.consent.screen": "true"
  }
}
JSON
  local create_output
  create_output=$($KCADM create client-scopes -r $REALM -f /tmp/scope_payload.json 2>&1)
  echo "$create_output" >&2
  local new_id
  new_id=$(echo "$create_output" | grep -oP "id '\K[a-f0-9-]+(?=')")
  if [ -n "$new_id" ]; then
    echo "$new_id"
  else
    get_scope_id "$scope_name"
  fi
}

echo "Creation/verification du client scope $SCOPE_READ_NAME (scope par defaut)"
SCOPE_READ_ID=$(create_scope_if_missing "$SCOPE_READ_NAME")
echo "  id=$SCOPE_READ_ID"

echo "Creation/verification du client scope $SCOPE_WRITE_NAME (scope optionnel)"
SCOPE_WRITE_ID=$(create_scope_if_missing "$SCOPE_WRITE_NAME")
echo "  id=$SCOPE_WRITE_ID"

# Attachement avec verification post-condition + retry : l'appel kcadm update
# peut echouer silencieusement sur un realm fraichement cree (observe sur une
# seconde machine) ; on ne masque plus l'erreur et on reessaie avant d'abandonner.
attach_scope() {
  local scope_type="$1"   # "default-client-scopes" ou "optional-client-scopes"
  local scope_id="$2"
  local scope_name="$3"

  if $KCADM get clients/$CLIENT_UUID/$scope_type -r $REALM 2>/dev/null | grep -q "\"id\" : \"$scope_id\""; then
    echo "  $scope_name deja attache ($scope_type)"
    return 0
  fi

  local out
  for attempt in 1 2 3; do
    if out=$($KCADM update clients/$CLIENT_UUID/$scope_type/$scope_id -r $REALM 2>&1); then
      echo "  $scope_name attache ($scope_type)"
      return 0
    fi
    echo "  tentative $attempt/3 echouee pour $scope_name : $out" >&2
    sleep 2
  done

  echo "ERREUR : attachement de $scope_name ($scope_type) impossible : $out" >&2
  return 1
}

echo "Attachement de $SCOPE_READ_NAME comme scope PAR DEFAUT du client $CLIENT_ID"
attach_scope "default-client-scopes" "$SCOPE_READ_ID" "$SCOPE_READ_NAME"

echo "Attachement de $SCOPE_WRITE_NAME comme scope OPTIONNEL du client $CLIENT_ID"
attach_scope "optional-client-scopes" "$SCOPE_WRITE_ID" "$SCOPE_WRITE_NAME"

echo "Scopes OAuth configures avec succes (cdc B.5, distincts du RBAC)."

echo "Initialisation Keycloak terminee avec succes."
