#!/usr/bin/env bash
# Prueba de conectividad manual contra el backend SGD (login + rutas /api/cargos).
#
# Hace login y llama GET /api/cargos/me, GET /api/cargos/oficinas y, si se indica
# depe_id, GET /api/cargos/documentos con el scope/periodo indicados. Imprime codigo
# HTTP, tiempo de respuesta y cuerpo de cada paso, y cierra sesion al final.
# Sirve para comparar el comportamiento del SGD entre el ambiente local y el
# publicado cuando la aplicacion falla (ver docs/pruebas-conexion-sgd.md).
#
# Uso:
#   ./scripts/test_sgd_connection.sh
#   SGD_URL="https://digital.regionhuanuco.gob.pe/" SGD_USER="waguirre" \
#     ./scripts/test_sgd_connection.sh personal 45 2025
#
# Variables de entorno opcionales: SGD_URL, SGD_USER, SGD_PASS.
# Argumentos posicionales opcionales: SCOPE DEPE_ID PERIOD.

set -u

# ---- Editar aca si preferis no pasar variables cada vez ----
SERVICE_URL="${SGD_URL:-https://digital.regionhuanuco.gob.pe/}"
USERNAME="${SGD_USER:-}"   # ej: "waguirre"; si queda vacio se pide interactivo
PASSWORD="${SGD_PASS:-}"   # dejar vacio: se pide oculto, no queda en el archivo ni en el historial
# --------------------------------------------------------------

SCOPE="${1:-personal}"
DEPE_ID="${2:-}"
PERIOD="${3:-$(date +%Y)}"
SERVICE_URL="${SERVICE_URL%/}/"

if [ -z "$USERNAME" ]; then
    read -r -p "Usuario SGD: " USERNAME
fi
if [ -z "$PASSWORD" ]; then
    read -r -s -p "Clave SGD: " PASSWORD
    echo
fi

TMP_BODY="$(mktemp)"
trap 'rm -f "$TMP_BODY"' EXIT

# request METHOD URL [JSON_BODY] [BEARER_TOKEN]
# Deja el status en $STATUS y el cuerpo en $BODY; los imprime tambien.
request() {
    method="$1"; url="$2"; data="${3:-}"; token="${4:-}"
    set -- curl -sS -o "$TMP_BODY" -w '%{http_code}' -X "$method" -H "Accept: application/json"
    if [ -n "$data" ]; then
        set -- "$@" -H "Content-Type: application/json" -d "$data"
    fi
    if [ -n "$token" ]; then
        set -- "$@" -H "Authorization: Bearer $token"
    fi
    start_ms=$(date +%s%3N 2>/dev/null || echo 0)
    STATUS=$("$@" "$url")
    end_ms=$(date +%s%3N 2>/dev/null || echo 0)
    BODY="$(cat "$TMP_BODY")"
    echo "Status: $STATUS  ($((end_ms - start_ms)) ms)"
    echo "$BODY"
    echo
}

echo "== POST ${SERVICE_URL}api/cargos/login =="
request POST "${SERVICE_URL}api/cargos/login" "{\"adm_email\":\"$USERNAME\",\"password\":\"$PASSWORD\"}"
LOGIN_STATUS="$STATUS"
LOGIN_BODY="$BODY"

if ! [ "$LOGIN_STATUS" -ge 200 ] 2>/dev/null || [ "$LOGIN_STATUS" -ge 300 ]; then
    echo "Login fallido, no se puede continuar."
    exit 1
fi

TOKEN=$(printf '%s' "$LOGIN_BODY" | grep -o '"token":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
    echo "La respuesta no trajo 'token'."
    exit 1
fi

echo "== GET ${SERVICE_URL}api/cargos/me =="
request GET "${SERVICE_URL}api/cargos/me" "" "$TOKEN"

echo "== GET ${SERVICE_URL}api/cargos/oficinas =="
request GET "${SERVICE_URL}api/cargos/oficinas" "" "$TOKEN"

if [ -n "$DEPE_ID" ]; then
    FECHA_DESDE="${PERIOD}-01-01"
    FECHA_HASTA="${PERIOD}-12-31"
    DOCS_URL="${SERVICE_URL}api/cargos/documentos?scope=${SCOPE}&depe_id=${DEPE_ID}&page=1&per_page=5&include_files=0&fecha_desde=${FECHA_DESDE}&fecha_hasta=${FECHA_HASTA}&with_total=1"
    echo "== GET $DOCS_URL =="
    request GET "$DOCS_URL" "" "$TOKEN"
else
    echo "Sugerencia: pasa depe_id como segundo argumento para probar la ruta de documentos, ej:"
    echo "  ./scripts/test_sgd_connection.sh personal 45 2025"
fi

echo "== POST ${SERVICE_URL}api/cargos/logout =="
request POST "${SERVICE_URL}api/cargos/logout" "" "$TOKEN"
