#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
pilot_build="$repo_root/.build/pilot"
pilot_repo="$pilot_build/SysML-v2-Pilot-Implementation"
pilot_jar="$repo_root/lib/org.omg.sysml.interactive-0.64.0-SNAPSHOT-all.jar"
pilot_library="$pilot_repo/sysml.library"

mkdir -p "$pilot_build" "$repo_root/lib"

if [[ -s "$pilot_jar" && -d "$pilot_library" ]]; then
  echo "Official SysML v2 Pilot parser already installed"
  exit 0
fi

if [[ ! -d "$pilot_repo/.git" ]]; then
  git clone --depth 1 https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation.git "$pilot_repo"
fi

cd "$pilot_repo"
./mvnw -pl org.omg.sysml.model,org.omg.sysml.logic -am -DskipTests install
./mvnw -pl org.omg.kerml.xtext,org.omg.sysml.xtext,org.omg.kerml.xtext.ide,org.omg.sysml.xtext.ide,org.omg.sysml.interactive -am -DskipTests package

cp "org.omg.sysml.interactive/target/org.omg.sysml.interactive-0.64.0-SNAPSHOT-all.jar" "$pilot_jar"

if [[ ! -d "$pilot_library" ]]; then
  echo "Official Pilot library directory was not produced" >&2
  exit 1
fi

echo "Official SysML v2 Pilot parser installed"
