#!/usr/bin/env bash
# Generates the Mosquitto password file used by the broker.
#
# Usage:
#   ./gen-passwd.sh
#
# Reads MQTT_USER / MQTT_PASS from the environment when no args are given, so
# the installer can call it after generating random credentials in .env.
set -euo pipefail

USER_ARG="${1:-${MQTT_USER:-guardioes}}"
PASS_ARG="${2:-${MQTT_PASS:-}}"

if [ -z "$PASS_ARG" ]; then
  echo "Erro: informe a senha (arg 2) ou defina MQTT_PASS." >&2
  exit 1
fi

OUT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_FILE="$OUT_DIR/passwd"

# Remove passwd antigo para evitar erro do mosquitto_passwd -c
rm -f "$OUT_FILE"

# Use the mosquitto image so no local install is required.
docker run --rm -v "$OUT_DIR":/out eclipse-mosquitto:2 \
  mosquitto_passwd -c -b /out/passwd "$USER_ARG" "$PASS_ARG"

echo "Arquivo de senha gerado em: $OUT_FILE (usuario: $USER_ARG)"

# Ajusta permissões para o usuário mosquitto (UID 1883) poder ler
chown 1883:1883 "$OUT_FILE"
chmod 644 "$OUT_FILE"
