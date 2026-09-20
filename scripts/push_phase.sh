#!/usr/bin/env bash
# Commit the current tree, tag it, and push branch + tag to origin. Never force-pushes.
#
# Usage (from the repository root):
#   scripts/push_phase.sh v0.1.0 "feat: add skeleton, oligo QC and report skeleton"
#
# What it does, in order:
#   1. checks that you are in the repo root and that the tag matches pyproject.toml
#   2. initialises git / adds the origin remote if needed (never rewrites an existing remote)
#   3. refuses to continue if a .env file would be committed
#   4. if origin already has commits (e.g. GitHub created a README) and you have none locally,
#      it bases your work on them without touching your files
#   5. commits everything with your message, creates an annotated tag, pushes branch and tag
#
# The script stops at the first problem and tells you what to fix.
set -euo pipefail

REPO_URL="${QPCR_REPO_URL:-https://github.com/zmeel/qpcr-assay-check.git}"
BRANCH="${QPCR_BRANCH:-main}"

die() { echo "ERROR: $*" >&2; exit 1; }

TAG="${1:-}"; MSG="${2:-}"
[[ -n "$TAG" && -n "$MSG" ]] || die 'usage: scripts/push_phase.sh <tag, e.g. v0.1.0> "<conventional commit message>"'
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "tag '$TAG' must look like v0.1.0"
[[ "$MSG" =~ ^(feat|fix|docs|test|chore|refactor|ci|build|perf)(\(.+\))?!?:\ .+ ]] \
  || die "commit message must follow Conventional Commits, e.g. 'feat: add remote BLAST backend'"
[[ -f pyproject.toml ]] || die "run this from the repository root (pyproject.toml not found)"

PYVER="$(sed -nE 's/^version *= *"([^"]+)".*/\1/p' pyproject.toml | head -n1)"
[[ "v$PYVER" == "$TAG" ]] || die "tag $TAG does not match pyproject.toml version $PYVER"

command -v git >/dev/null || die "git is not installed"
git config user.name  >/dev/null || die "set your identity first: git config --global user.name 'Your Name'"
git config user.email >/dev/null || die "set your identity first: git config --global user.email 'you@example.org'"

if [[ ! -d .git ]]; then
  git init -q -b "$BRANCH"
  echo "Initialised a new git repository on branch $BRANCH"
fi

if git remote get-url origin >/dev/null 2>&1; then
  CURRENT="$(git remote get-url origin)"
  norm() { local u="${1%.git}"; u="${u#git@github.com:}"; u="${u#https://github.com/}"; echo "$u"; }
  if [[ "$(norm "$CURRENT")" != "$(norm "$REPO_URL")" && -z "${QPCR_REPO_URL:-}" ]]; then
    die "origin is '$CURRENT', expected '$REPO_URL'. Fix it yourself: git remote set-url origin $REPO_URL"
  fi
else
  git remote add origin "$REPO_URL"
  echo "Added remote origin -> $REPO_URL"
fi

# Never commit secrets.
if [[ -f .env ]] && ! git check-ignore -q .env; then
  die ".env exists but is not ignored by .gitignore; refusing to continue"
fi
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  die ".env is tracked by git; remove it from the index (git rm --cached .env) first"
fi

git checkout -q -B "$BRANCH" 2>/dev/null || git checkout -q "$BRANCH"

REMOTE_HAS_BRANCH=0
if git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
  REMOTE_HAS_BRANCH=1
  git fetch -q origin "$BRANCH"
  if ! git rev-parse --verify -q HEAD >/dev/null; then
    # No local commits yet: adopt the remote history, keep the working tree exactly as it is.
    git reset -q "origin/$BRANCH"
    echo "Based your files on the existing origin/$BRANCH history"
  elif ! git merge-base --is-ancestor "origin/$BRANCH" HEAD; then
    die "origin/$BRANCH has commits that your local branch does not contain. Run: git pull --rebase origin $BRANCH  (then re-run this script)"
  fi
fi

if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then die "tag $TAG already exists locally"; fi
if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then die "tag $TAG already exists on origin"; fi

git add -A
if git diff --cached --quiet && git rev-parse --verify -q HEAD >/dev/null; then
  echo "Nothing new to commit; tagging the current commit."
else
  git commit -q -m "$MSG"
fi

git tag -a "$TAG" -m "$MSG"
git push -u origin "$BRANCH"
git push origin "$TAG"

echo
echo "Pushed. Commit: $(git rev-parse --short HEAD)   Tag: $TAG"
echo "Branch: $BRANCH   Remote: $(git remote get-url origin)"
