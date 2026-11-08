# VektaIO web (React + TypeScript). CI runs `just ci`.
set dotenv-load := true

setup:
    pnpm install

dev:
    pnpm dev

format:
    pnpm exec prettier --write .

lint:
    pnpm exec eslint . --max-warnings=0

typecheck:
    pnpm exec tsc --noEmit

test:
    pnpm exec vitest run --coverage

e2e:
    pnpm exec playwright test

gen:
    pnpm run gen

build:
    pnpm build

# Design tokens → generated theme (add --check to verify only)
tokens *args:
    "$(git rev-parse --show-toplevel)/scripts/tokens.sh" {{args}}

# Everything CI checks on every PR
ci:
    just tokens --check
    pnpm exec prettier --check .
    just lint
    just typecheck
    pnpm exec knip
    just test
    just build

deploy env:
    @echo "TODO: deploy to {{env}} (e.g. upload dist/ to your host/CDN)"; exit 1
