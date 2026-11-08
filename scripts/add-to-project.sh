#!/usr/bin/env bash
# Add VektaIO shared skills + the Claude dev pipeline to the current project.
# Usage: add-to-project.sh <web|api|mobile|monorepo>
#   web | api | mobile  — single-app repository
#   monorepo            — one repository with apps/api, apps/web, apps/mobile and a shared API contract
# Never overwrites existing files — it saves a *.vekta-template copy next to them instead.
set -euo pipefail

TYPE="${1:-}"
[ "$TYPE" = "fullstack" ] && TYPE="monorepo"
case "$TYPE" in web|api|mobile|monorepo) ;; *)
  echo "Usage: $0 <web|api|mobile|monorepo>" >&2; exit 1;;
esac

REPO_RAW="${VEKTA_SKILLS_RAW:-https://raw.githubusercontent.com/VektaIO/engineering-skills/main}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
LOCAL_ROOT=""
[ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/../templates" ] && LOCAL_ROOT="$SCRIPT_DIR/.."

get() { # <path under repo> -> stdout
  if [ -n "$LOCAL_ROOT" ]; then cat "$LOCAL_ROOT/$1"; else curl -fsSL "$REPO_RAW/$1"; fi
}

place() { # <dest> [mode] (content on stdin)
  local dest="$1" mode="${2:-}" tmp; tmp="$(mktemp)"; cat > "$tmp"
  mkdir -p "$(dirname "$dest")"
  if [ -e "$dest" ]; then
    if cmp -s "$tmp" "$dest"; then rm -f "$tmp"; echo "= $dest (unchanged)"; return; fi
    chmod 644 "$tmp"; mv "$tmp" "$dest.vekta-template"; echo "! $dest exists — new version saved as $dest.vekta-template (merge manually)"
  else
    mv "$tmp" "$dest"; chmod 644 "$dest"; [ -n "$mode" ] && chmod 755 "$dest"; echo "+ $dest"
  fi
}

if [ "$TYPE" = "monorepo" ]; then
  STACKS="web api mobile"; WD_WEB="apps/web"; WD_API="apps/api"; WD_MOBILE="apps/mobile"
else
  STACKS="$TYPE"; WD_WEB="."; WD_API="."; WD_MOBILE="."
fi
wd_for() { case "$1" in web) echo "$WD_WEB";; api) echo "$WD_API";; mobile) echo "$WD_MOBILE";; esac; }
release_type_for() { case "$1" in web) echo node;; api) echo python;; mobile) echo dart;; esac; }

STACK_PLUGINS=""
for s in $STACKS; do STACK_PLUGINS+="            vekta-${s}@vektaio-skills"$'\n'; done
[ "$TYPE" != "api" ] && STACK_PLUGINS+="            vekta-design@vektaio-skills"$'\n'
STACK_PLUGINS="${STACK_PLUGINS%$'\n'}"

subst() { # replace placeholders in workflow templates
  local sp_file; sp_file="$(mktemp)"; printf '%s\n' "$STACK_PLUGINS" > "$sp_file"
  sed -e "s#__WORKDIR_WEB__#${WD_WEB}#g" -e "s#__WORKDIR_API__#${WD_API}#g" -e "s#__WORKDIR_MOBILE__#${WD_MOBILE}#g" \
    | awk -v f="$sp_file" '/^__STACK_PLUGINS__$/ { while ((getline line < f) > 0) print line; next } { print }'
  rm -f "$sp_file"
}

if [ "$TYPE" = "monorepo" ]; then
  echo "== Monorepo skeleton (apps/api, apps/web, apps/mobile, packages/contract)"
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    mode=""; case "$f" in scripts/*.sh) mode="+x";; esac
    get "templates/monorepo/$f" | place "$f" "$mode"
  done < <(get "templates/monorepo/FILES")
else
  echo "== Claude skills ($TYPE)"
  get "templates/$TYPE/.claude/settings.json" | place ".claude/settings.json"
  get "templates/$TYPE/CLAUDE.md" | place "CLAUDE.md"
fi

echo "== GitHub pipeline"
for wf in branch-policy claude-review claude; do
  get "templates/github/workflows/$wf.yml" | subst | place ".github/workflows/$wf.yml"
done
if [ "$TYPE" != "monorepo" ]; then
  get "templates/github/workflows/ci-$TYPE.yml" | subst | place ".github/workflows/ci-$TYPE.yml"
  for wf in deploy-staging release; do
    get "templates/github/workflows/$wf.yml" | subst | place ".github/workflows/$wf.yml"
  done
  get "templates/github/CODEOWNERS" | place ".github/CODEOWNERS"
  get "templates/github/release-please-config.json" | sed "s/\"release-type\": \"simple\"/\"release-type\": \"$(release_type_for "$TYPE")\"/" | place "release-please-config.json"
  get "templates/github/.release-please-manifest.json" | place ".release-please-manifest.json"
fi
get "templates/github/pull_request_template.md" | place ".github/pull_request_template.md"
{
  get "templates/github/dependabot.head.yml"
  for s in $STACKS; do d="/$(wd_for "$s")"; d="${d%/.}"; [ -z "$d" ] && d="/"; get "templates/github/dependabot.$s.yml" | sed "s#__DIR__#${d}#"; done
} | place ".github/dependabot.yml"

if [ "$TYPE" != "api" ]; then
  echo "== Design identity (unique to this product)"
  if [ "$TYPE" = "monorepo" ]; then DDIR="packages/design"; else DDIR="design"; fi
  get "templates/design/tokens.json" | place "$DDIR/tokens.json"
  get "templates/design/design.md" | place "$DDIR/design.md"
  get "templates/design/config.$TYPE.json" | place "$DDIR/design.config.json"
  get "templates/design/build_tokens.py" | place "scripts/build_tokens.py" +x
  get "templates/design/tokens.sh" | place "scripts/tokens.sh" +x
  case "$TYPE" in
    web) get "templates/design/prettierignore" | place ".prettierignore";;
    monorepo) get "templates/design/prettierignore" | place "apps/web/.prettierignore";;
  esac
  if command -v python3 >/dev/null 2>&1; then
    python3 scripts/build_tokens.py "$DDIR/design.config.json" >/dev/null && echo "+ generated theme (CSS + theme runtime / Flutter theme + controller) and $DDIR/preview.html (example tokens)"
  fi
fi

echo "== Task runner (just)"
for s in $STACKS; do
  get "templates/github/justfiles/$s.just" | place "$(wd_for "$s")/justfile"
done

SETUP="$( [ -n "$LOCAL_ROOT" ] && echo "$(cd "$LOCAL_ROOT" && pwd)/scripts/setup-github.sh $TYPE" || echo "curl -fsSL $REPO_RAW/scripts/setup-github.sh | bash -s -- $TYPE" )"
cat <<EOF

Done. Next:
  0. Give this product its own look: in Claude Code run  /vekta-design:design-direction  (replaces the example tokens)
  1. Fill the <placeholders> in CLAUDE.md$( [ "$TYPE" = "monorepo" ] && echo " and apps/*/CLAUDE.md" ) and the TODOs in the justfile deploy recipes.
  2. Ask Claude to scaffold the app$( [ "$TYPE" = "monorepo" ] && echo "s inside apps/api, apps/web, apps/mobile" ) following the skills.
  3. Commit, push to main, then one-time GitHub setup:  $SETUP
EOF
