# VektaIO mobile (Flutter). CI runs `just ci`; PRs to main also run `just build-check`.

setup:
    flutter pub get
    dart run build_runner build --delete-conflicting-outputs

dev:
    flutter run --flavor dev -t lib/main_dev.dart --dart-define-from-file=config/dev.json

format:
    dart format .

lint:
    flutter analyze --fatal-infos

gen:
    dart run build_runner build --delete-conflicting-outputs
    flutter gen-l10n

test:
    flutter test --coverage --test-randomize-ordering-seed random

e2e:
    patrol test --flavor dev

# Design tokens → generated theme (add --check to verify only)
tokens *args:
    "$(git rev-parse --show-toplevel)/scripts/tokens.sh" {{args}}

# Everything CI checks on every PR
ci:
    just tokens --check
    dart format --set-exit-if-changed .
    just gen
    git diff --exit-code -- lib
    just lint
    just test

# Release gate (PRs into main): production flavor builds. Version name comes from pubspec.yaml (bumped by release-please); build number from CI.
build-check:
    flutter build appbundle --flavor prod -t lib/main_prod.dart --dart-define-from-file=config/prod.json --build-number "${GITHUB_RUN_NUMBER:-1}" --obfuscate --split-debug-info=build/symbols

deploy env:
    @echo "TODO: upload to Play internal / TestFlight via fastlane for {{env}}"; exit 1
