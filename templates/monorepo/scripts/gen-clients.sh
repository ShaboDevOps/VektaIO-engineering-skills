#!/usr/bin/env bash
# Export the OpenAPI contract from apps/api and regenerate the web (TypeScript) and mobile (Dart) clients.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# Pin to a version you have verified; bump deliberately (generated code changes between versions).
OPENAPI_GENERATOR_IMAGE="${OPENAPI_GENERATOR_IMAGE:-openapitools/openapi-generator-cli:v7.10.0}"

echo "→ exporting contract"
(cd apps/api && uv run python -m scripts.export_openapi) > packages/contract/openapi.json

echo "→ web: TypeScript types"
(cd apps/web && pnpm exec openapi-typescript ../../packages/contract/openapi.json -o src/shared/api/schema.d.ts)

echo "→ mobile: Dart client"
docker run --rm -u "$(id -u):$(id -g)" -v "$ROOT:/local" "$OPENAPI_GENERATOR_IMAGE" generate \
  -i /local/packages/contract/openapi.json -g dart-dio \
  -o /local/apps/mobile/packages/api_client \
  --additional-properties=pubName=api_client,serializationLibrary=json_serializable >/dev/null
(cd apps/mobile/packages/api_client && dart pub get >/dev/null && dart run build_runner build --delete-conflicting-outputs >/dev/null)

echo "✓ contract and clients regenerated — commit packages/contract, apps/web/src/shared/api, apps/mobile/packages/api_client"
