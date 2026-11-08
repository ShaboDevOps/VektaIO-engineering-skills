#!/usr/bin/env bash
# CI contract gate:
#  1. the committed contract and clients match the API code (someone forgot `just gen` otherwise)
#  2. no breaking changes compared with the base branch (BASE, default develop)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${BASE:-develop}"
# TODO: pin to a specific oasdiff version tag once verified.
OASDIFF_IMAGE="${OASDIFF_IMAGE:-tufin/oasdiff:latest}"

./scripts/gen-clients.sh
if ! git diff --quiet -- packages/contract apps/web/src/shared/api apps/mobile/packages/api_client; then
  git diff --stat -- packages/contract apps/web/src/shared/api apps/mobile/packages/api_client
  echo "::error::Contract or generated clients are out of date — run 'just gen' and commit the result."
  exit 1
fi

if git cat-file -e "origin/$BASE:packages/contract/openapi.json" 2>/dev/null; then
  mkdir -p .contract-base
  git show "origin/$BASE:packages/contract/openapi.json" > .contract-base/openapi.json
  docker run --rm -v "$ROOT:/specs" "$OASDIFF_IMAGE" breaking \
    /specs/.contract-base/openapi.json /specs/packages/contract/openapi.json --fail-on ERR \
    || { echo "::error::Breaking API change vs $BASE — add a new API version with deprecation headers instead."; exit 1; }
  rm -rf .contract-base
else
  echo "No contract on origin/$BASE yet — skipping breaking-change check."
fi
echo "✓ contract OK"
