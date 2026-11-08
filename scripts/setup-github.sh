#!/usr/bin/env bash
# One-time GitHub setup for the VektaIO branch model. Run from the project root after the
# pipeline files are on the default branch. Requires: gh (logged in, repo admin).
# Usage: setup-github.sh <web|api|mobile|monorepo> [owner/repo]
# Approvals: APPROVALS_DEVELOP=1 APPROVALS_MAIN=2 setup-github.sh api   (defaults 1 / 1; use 2 on main once the team has 3+ devs).
# GitHub never lets authors approve their own PR, so a solo developer needs a teammate reviewer (or set 0).
#
# Note: branch protection and environment reviewers on PRIVATE repos need a paid GitHub plan
# (Pro/Team/Enterprise). On the free plan the script reports what it couldn't set.
set -uo pipefail

TYPE="${1:-}"
[ "$TYPE" = "fullstack" ] && TYPE="monorepo"
case "$TYPE" in web|api|mobile|monorepo) ;; *)
  echo "Usage: $0 <web|api|mobile|monorepo> [owner/repo]" >&2; exit 1;;
esac
REPO="${2:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
echo "Configuring $REPO ($TYPE)"

case "$TYPE" in
  web)       CHECKS='"ci-web"';;
  api)       CHECKS='"ci-api"';;
  mobile)    CHECKS='"ci-mobile"';;
  monorepo)  CHECKS='"ci"';;   # aggregator job: passes when every affected app passed
esac
CHECKS="$CHECKS,\"branch-policy\",\"claude-review\""
case "$TYPE" in
  web)       MAIN_EXTRA='"e2e-web"';;
  api)       MAIN_EXTRA='"api-contract"';;
  mobile)    MAIN_EXTRA='"build-mobile"';;
  monorepo)  MAIN_EXTRA='';;  # release gates run inside the ci workflow for PRs into main
esac

ok()   { echo "  ✓ $1"; }
warn() { echo "  ! $1"; }

# 1. develop branch from main
DEFAULT="$(gh api "repos/$REPO" --jq .default_branch)"
if gh api "repos/$REPO/branches/develop" >/dev/null 2>&1; then
  ok "develop exists"
else
  SHA="$(gh api "repos/$REPO/git/ref/heads/$DEFAULT" --jq .object.sha)"
  gh api -X POST "repos/$REPO/git/refs" -f ref=refs/heads/develop -f sha="$SHA" >/dev/null \
    && ok "created develop from $DEFAULT" || warn "could not create develop"
fi

# 2. repo settings: develop is default (feature PRs target it), squash + merge commits, auto-delete branches
gh api -X PATCH "repos/$REPO" \
  -f default_branch=develop \
  -F allow_squash_merge=true -F allow_merge_commit=true -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true -F allow_auto_merge=false \
  -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY >/dev/null \
  && ok "repo settings (default branch develop, squash + merge commits, delete merged branches)" \
  || warn "could not update repo settings"

# 3. branch protection
protect() { # branch approvals checks
  gh api -X PUT "repos/$REPO/branches/$1/protection" --input - >/dev/null <<JSON
{
  "required_status_checks": { "strict": true, "contexts": [$3] },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": $2,
    "require_code_owner_reviews": true,
    "dismiss_stale_reviews": true,
    "require_last_push_approval": true
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
}
protect develop "${APPROVALS_DEVELOP:-1}" "$CHECKS" && ok "protected develop (PR + ${APPROVALS_DEVELOP:-1} approval(s) + checks: ${CHECKS})" || warn "could not protect develop (private repo on free plan?)"
protect main "${APPROVALS_MAIN:-1}" "$CHECKS${MAIN_EXTRA:+,$MAIN_EXTRA}" && ok "protected main (PR + ${APPROVALS_MAIN:-1} approval(s) + checks incl. release gates: ${MAIN_EXTRA})"              || warn "could not protect main (private repo on free plan?)"

# 4. environments
gh api -X PUT "repos/$REPO/environments/staging" >/dev/null && ok "environment: staging" || warn "could not create staging environment"
ME_ID="$(gh api user --jq .id)"
gh api -X PUT "repos/$REPO/environments/production" --input - >/dev/null <<JSON && ok "environment: production (requires your approval to deploy)" || warn "could not add production reviewers (needs paid plan for private repos)"
{ "reviewers": [ { "type": "User", "id": ${ME_ID} } ], "deployment_branch_policy": { "protected_branches": false, "custom_branch_policies": true } }
JSON
gh api -X POST "repos/$REPO/environments/production/deployment-branch-policies" -f name='v*' -f type=tag >/dev/null 2>&1 \
  && ok "production deploys only from v* tags" || warn "could not restrict production to tags"

# 5. secrets
echo
if gh secret list -R "$REPO" | grep -q '^CLAUDE_CODE_OAUTH_TOKEN'; then
  ok "secret CLAUDE_CODE_OAUTH_TOKEN present"
else
  warn "missing secret CLAUDE_CODE_OAUTH_TOKEN — run 'claude setup-token', then: gh secret set CLAUDE_CODE_OAUTH_TOKEN -R $REPO"
fi
gh secret list -R "$REPO" | grep -q '^RELEASE_PLEASE_TOKEN' \
  && ok "secret RELEASE_PLEASE_TOKEN present" \
  || warn "recommended: secret RELEASE_PLEASE_TOKEN (fine-grained PAT: contents + pull requests write) so CI runs on Release and back-merge PRs"

cat <<EOF

Also do once:
  • Install the Claude GitHub App on this repo:  run '/install-github-app' in Claude Code, or https://github.com/apps/claude
  • Make sure the Claude GitHub App can read VektaIO/engineering-skills (or make that repo public — it contains no secrets)
  • Replace @VektaIO/engineering in .github/CODEOWNERS with real users/teams
EOF
