#!/usr/bin/env python3
"""VektaIO branch guard for Claude Code (PreToolUse on Bash).

Blocks, with an explanation for Claude:
  - pushing to develop/main/master (work goes through pull requests)
  - force pushes without --force-with-lease
  - merging PRs (`gh pr merge`) — humans merge
  - committing or merging locally while on develop/main/master
Exit code 2 = block (stderr is shown to Claude). Exit 0 = allow.
"""
import json
import re
import subprocess
import sys

PROTECTED = ("main", "master", "develop")


def current_branch(cwd: str | None) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd or None, capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def block(reason: str) -> None:
    print(f"Blocked by VektaIO pipeline guard: {reason}", file=sys.stderr)
    sys.exit(2)


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        sys.exit(0)
    cwd = data.get("cwd")
    prot = "|".join(PROTECTED)

    # Split compound commands so each part is checked.
    for part in re.split(r"&&|\|\||;|\n", cmd):
        p = part.strip()
        if not p:
            continue

        if re.search(r"\bgh\s+pr\s+merge\b", p):
            block("merging pull requests is a human decision. Open/update the PR and stop.")

        if re.search(r"\bgit\s+push\b", p):
            if re.search(r"(\s--force(\s|$)|\s-f(\s|$))", p) and "--force-with-lease" not in p:
                block("plain force push is not allowed. Use `git push --force-with-lease` on your own branch.")
            if re.search(rf"(\s|:|/)({prot})(\s|$)", p):
                block(f"pushing to {'/'.join(PROTECTED)} is not allowed. Push your feat/fix/patch branch and open a PR.")
            # `git push` with no refspec while on a protected branch
            if current_branch(cwd) in PROTECTED and not re.search(r"\bgit\s+push\s+\S+\s+\S+", p):
                block(f"you are on '{current_branch(cwd)}'. Create a branch with /vekta-core:start first.")

        if re.search(r"\bgit\s+(commit|merge|cherry-pick|rebase\s+--continue)\b", p):
            br = current_branch(cwd)
            if br in PROTECTED:
                block(f"don't commit or merge directly on '{br}'. Create a feat/fix/patch branch with /vekta-core:start.")

    sys.exit(0)


if __name__ == "__main__":
    main()
