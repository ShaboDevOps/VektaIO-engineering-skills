#!/usr/bin/env bash
# Build (or with --check, verify) this project's design tokens. Finds the design config automatically:
#   packages/design/design.config.json  (monorepo)   or   design/design.config.json  (single app)
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || (cd "$(dirname "$0")/.." && pwd))"
for c in "$ROOT/packages/design/design.config.json" "$ROOT/design/design.config.json"; do
  if [ -f "$c" ]; then exec python3 "$ROOT/scripts/build_tokens.py" "$c" "$@"; fi
done
echo "No design config found (packages/design/ or design/). Run /vekta-design:design-direction first." >&2
exit 1
