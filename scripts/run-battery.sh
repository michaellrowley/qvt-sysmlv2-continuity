#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ ! -f target/sysml-v2-qvt-continuity-1.0.0-SNAPSHOT.jar ]]; then
  scripts/build.sh >/dev/null
fi

java -jar target/sysml-v2-qvt-continuity-1.0.0-SNAPSHOT.jar \
  qvt \
  --input examples/battery_lifecycle.sysml \
  --output target/battery-lifecycle.sysml \
  --transformation qvt/LifecycleOperational.qvto
