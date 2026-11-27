#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
lib_dir="$repo_root/lib"
mkdir -p "$lib_dir"

download() {
  local url="$1"
  local output="$2"
  if [[ -s "$output" ]]; then
    return
  fi
  curl --fail --location --silent --show-error "$url" --output "$output"
}

qvt_base="https://download.eclipse.org/mmt/qvto/builds/release/3.11.2/plugins"
ocl_base="https://download.eclipse.org/releases/2026-09/202609091000/plugins"

download "$qvt_base/org.eclipse.m2m.qvt.oml_3.11.2.v20260216-1113.jar" \
  "$lib_dir/org.eclipse.m2m.qvt.oml_3.11.2.v20260216-1113.jar"
download "$qvt_base/org.eclipse.m2m.qvt.oml.runtime_3.11.0.v20260216-1113.jar" \
  "$lib_dir/org.eclipse.m2m.qvt.oml.runtime_3.11.0.v20260216-1113.jar"
download "$qvt_base/org.eclipse.m2m.qvt.oml.common_3.11.0.v20260216-1113.jar" \
  "$lib_dir/org.eclipse.m2m.qvt.oml.common_3.11.0.v20260216-1113.jar"
download "$qvt_base/org.eclipse.m2m.qvt.oml.cst.parser_3.11.2.v20260216-1113.jar" \
  "$lib_dir/org.eclipse.m2m.qvt.oml.cst.parser_3.11.2.v20260216-1113.jar"
download "$qvt_base/org.eclipse.m2m.qvt.oml.emf.util_3.11.0.v20260216-1113.jar" \
  "$lib_dir/org.eclipse.m2m.qvt.oml.emf.util_3.11.0.v20260216-1113.jar"
download "$qvt_base/org.eclipse.m2m.qvt.oml.ecore.imperativeocl_3.11.0.v20260216-1113.jar" \
  "$lib_dir/org.eclipse.m2m.qvt.oml.ecore.imperativeocl_3.11.0.v20260216-1113.jar"
download "$ocl_base/org.eclipse.ocl_3.24.0.v20260601-1413.jar" \
  "$lib_dir/org.eclipse.ocl_3.24.0.v20260601-1413.jar"
download "$ocl_base/org.eclipse.ocl.common_1.24.0.v20260601-1413.jar" \
  "$lib_dir/org.eclipse.ocl.common_1.24.0.v20260601-1413.jar"
download "$ocl_base/org.eclipse.ocl.ecore_3.24.0.v20260601-1413.jar" \
  "$lib_dir/org.eclipse.ocl.ecore_3.24.0.v20260601-1413.jar"

scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$scripts_dir/install-pilot-sysml.sh"
