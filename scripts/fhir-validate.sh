#!/bin/sh
# Samples every answer /fhir gives on the demo seed and runs the pinned HL7 validator on them; fails on any error.
set -eu
cd "$(dirname "$0")/.."

VERSION=7.0.6
SHA256=2686590539f0b3ba7683149b25d78249f6886c04e2c326e884c5049d8947df89
JAR=".cache/fhir-validator/$VERSION/validator_cli.jar"
BASE_URL="${FHIR_BASE_URL:-http://localhost:8000}"
SAMPLES=$(mktemp -d)
trap 'rm -rf "$SAMPLES"' EXIT

command -v java >/dev/null || { echo "java 11+ is required" >&2; exit 1; }
if ! { [ -f "$JAR" ] && echo "$SHA256  $JAR" | shasum -a 256 -c - >/dev/null 2>&1; }; then
  mkdir -p "$(dirname "$JAR")"
  curl -fsSL -o "$JAR" "https://github.com/hapifhir/org.hl7.fhir.core/releases/download/$VERSION/validator_cli.jar"
  echo "$SHA256  $JAR" | shasum -a 256 -c -
fi

uv run python -m scripts.fhir_samples "$BASE_URL" "$SAMPLES"
java -jar "$JAR" "$SAMPLES" -version 4.0.1 -tx n/a -extension any -output "$SAMPLES/outcome.json" "$@" \
  | grep -E '^(Success|\*FAILURE\*|  Error|  Warning)|Error @' || true
uv run python -c "
import json, sys
outcome = json.load(open('$SAMPLES/outcome.json'))
errors = [i for e in outcome.get('entry', [outcome]) for i in e.get('resource', e).get('issue', []) if i['severity'] in ('error', 'fatal')]
print(f'{len(errors)} errors')
sys.exit(1 if errors else 0)
"
