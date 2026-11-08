#!/usr/bin/env bash
# Copy the VektaIO skills, agents and safety hook INTO a project's .claude/ folder, so Claude Code
# (desktop app or CLI) loads them automatically — no plugin install needed, and teammates get them via git.
# Re-run any time to pull the latest skills into the project.
# Usage: vendor-skills.sh <project-dir> [plugins...]   (default plugins: from the project's type)
set -euo pipefail
SRC="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$(cd "${1:?Usage: vendor-skills.sh <project-dir> [plugins...]}" && pwd)"
shift || true
if [ $# -gt 0 ]; then PLUGINS="$*"
elif [ -d "$DEST/apps/api" ] || [ -d "$DEST/apps/web" ] || [ -d "$DEST/apps/mobile" ]; then PLUGINS="vekta-core vekta-api vekta-web vekta-mobile vekta-design"
else PLUGINS="vekta-core"; fi

mkdir -p "$DEST/.claude/skills" "$DEST/.claude/agents" "$DEST/.claude/hooks"
for p in $PLUGINS; do
  [ -d "$SRC/plugins/$p" ] || { echo "unknown plugin $p" >&2; exit 1; }
  for s in "$SRC/plugins/$p"/skills/*/; do
    [ -d "$s" ] || continue
    name="$(basename "$s")"; mkdir -p "$DEST/.claude/skills/$name"
    cp -R "$s". "$DEST/.claude/skills/$name/"
    echo "+ skill  $name  ($p)"
  done
  for a in "$SRC/plugins/$p"/agents/*.md; do
    [ -f "$a" ] || continue; cp "$a" "$DEST/.claude/agents/"; echo "+ agent  $(basename "$a" .md)"
  done
  [ -f "$SRC/plugins/$p/hooks/guard_git.py" ] && cp "$SRC/plugins/$p/hooks/guard_git.py" "$DEST/.claude/hooks/" && echo "+ hook   guard_git.py"
done

# Project skills aren't namespaced: /vekta-core:ship -> /ship, vekta-design:ui-craft -> ui-craft
strip='s#/vekta-(core|design|web|api|mobile):#/#g; s#vekta-(core|design|web|api|mobile):##g'
# sed -i.bak works on both macOS (BSD) and Linux (GNU) sed; plain -i doesn't on macOS
strip_ns() { sed -E -i.bak "$strip" "$@" && for x in "$@"; do rm -f "$x.bak"; done; }
find "$DEST/.claude/skills" "$DEST/.claude/agents" -type f -name "*.md" -exec sed -E -i.bak "$strip" {} +
find "$DEST/.claude/skills" "$DEST/.claude/agents" -type f -name "*.md.bak" -delete
if [ -f "$DEST/.claude/hooks/guard_git.py" ]; then strip_ns "$DEST/.claude/hooks/guard_git.py"; fi
for f in "$DEST/CLAUDE.md" "$DEST"/apps/*/CLAUDE.md; do if [ -f "$f" ]; then strip_ns "$f"; fi; done

# settings.json: register the safety hook; drop plugin entries so skills don't load twice
python3 - "$DEST/.claude/settings.json" <<'PY'
import json, sys, os
p = sys.argv[1]
s = json.load(open(p)) if os.path.exists(p) else {}
s.pop("enabledPlugins", None); s.pop("extraKnownMarketplaces", None)
hook = {"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard_git.py\""}
pre = s.setdefault("hooks", {}).setdefault("PreToolUse", [])
if not any(h.get("command") == hook["command"] for m in pre for h in m.get("hooks", [])):
    pre.append({"matcher": "Bash", "hooks": [hook]})
json.dump(s, open(p, "w"), indent=2); open(p, "a").write("\n")
PY

REV="$(git -C "$SRC" rev-parse --short HEAD 2>/dev/null || echo unknown)"
cat > "$DEST/.claude/skills/README.md" <<MD
# VektaIO skills (vendored)

Copied from ShaboDevOps/VektaIO-engineering-skills @ $REV by \`scripts/vendor-skills.sh\`.
Don't edit here — change the skills repo, then re-run:
\`~/vektaio-engineering-skills/scripts/vendor-skills.sh .\`

Commands: /start · /ship · /promote · /review-pr · /design-direction
Agents: code-reviewer · qa-tester
MD
echo "Done — open a NEW Claude Code session in $DEST."
