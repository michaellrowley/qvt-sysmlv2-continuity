#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"

container_name="sysml-v2-continuity-api-test"

cleanup() {
  podman rm -f "$container_name" >/dev/null 2>&1 || true
}
trap cleanup EXIT

podman build --quiet --file Containerfile --tag sysml-v2-continuity-api:test .
podman rm -f "$container_name" >/dev/null 2>&1 || true
podman run \
  --detach \
  --name "$container_name" \
  --publish 127.0.0.1:8080:8080 \
  sysml-v2-continuity-api:test

for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8080/health >/dev/null; then
    break
  fi
  if [[ "$attempt" == "30" ]]; then
    echo "Test API did not become healthy" >&2
    exit 1
  fi
  sleep 1
done

python3 -m pytest -q tests/test_remote_api.py
python3 -m sysml_v2_qvt.cli battery --api-url http://127.0.0.1:8080 >/tmp/sysml-v2-battery-remote.json
python3 -m sysml_v2_qvt.cli impact --api-url http://127.0.0.1:8080 >/tmp/sysml-v2-impact-remote.json

python3 - <<'PY'
import json

with open("/tmp/sysml-v2-battery-remote.json", encoding="utf-8") as stream:
    battery = json.load(stream)
with open("/tmp/sysml-v2-impact-remote.json", encoding="utf-8") as stream:
    impact = json.load(stream)

assert battery["passed"] is True
assert battery["diagnostics"] == []
assert impact["impact"]["root"] == "R-BATT-THERMAL@2"
print("Remote battery lifecycle and impact propagation passed")
PY
