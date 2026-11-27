#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

scripts/download-qvt-libs.sh
scripts/install-pilot-sysml.sh
mvn test package
