#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

git submodule sync --recursive
git submodule update --init --recursive

check_pin() {
  local path="$1"
  local expected="$2"

  if [[ ! -e "$path" ]]; then
    echo "ERROR: submodule path missing: $path" >&2
    return 1
  fi

  local actual
  actual="$(git -C "$path" rev-parse HEAD)"
  if [[ "$actual" != "$expected" ]]; then
    echo "ERROR: $path is at $actual; expected pinned revision $expected" >&2
    echo "Review the upstream diff, update docs/REUSE_PLAN.md and THIRD_PARTY_NOTICES.md, then change this pin deliberately." >&2
    return 1
  fi

  echo "OK: $path @ $actual"
}

check_pin "third_party/upstream/crforge" "fa5959055c590a493d62c8dbc804e602832d08a6"
check_pin "third_party/upstream/royalegym" "278bcb06dae717b89194b992235a9fa8a5209084"
check_pin "third_party/upstream/royalesim" "a849c29ae632e12f81442c45b0d9b2d2f2f99f15"

echo "Upstream source pins verified."
