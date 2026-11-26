#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

podman build --file Containerfile --tag sysml-v2-continuity-api:latest .
podman rm -f sysml-v2-continuity-api >/dev/null 2>&1 || true
podman run \
  --detach \
  --name sysml-v2-continuity-api \
  --publish 127.0.0.1:8080:8080 \
  sysml-v2-continuity-api:latest

echo "SysML v2 test API: http://127.0.0.1:8080"
