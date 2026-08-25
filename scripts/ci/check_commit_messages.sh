#!/usr/bin/env bash
# Validates commit subjects against Conventional Commits
# (https://www.conventionalcommits.org/), used by
# .github/workflows/commitlint.yml to block a PR whose commits don't follow
# the convention. This isn't just style: release.yml's compute_release.py
# parses these prefixes to decide the next version's major/minor/patch bump,
# so an unparseable commit silently falls out of that calculation.
set -euo pipefail

BASE_REF="${1:?usage: check_commit_messages.sh <base-ref> <head-ref>}"
HEAD_REF="${2:?usage: check_commit_messages.sh <base-ref> <head-ref>}"

TYPES='feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert'
PATTERN="^(${TYPES})(\([a-z0-9./_-]+\))?!?: .+"

fail=0
while IFS=$'\t' read -r sha subject; do
  [ -z "$sha" ] && continue
  # Merge commits aren't authored against the convention.
  case "$subject" in
    "Merge "*) continue ;;
  esac
  if ! [[ "$subject" =~ $PATTERN ]]; then
    echo "::error::Commit $sha does not follow Conventional Commits: \"$subject\""
    fail=1
  fi
done < <(git log --no-merges --format='%h%x09%s' "$BASE_REF..$HEAD_REF")

if [ "$fail" -ne 0 ]; then
  echo ""
  echo "Expected format: type(scope)?: description"
  echo "Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert"
  echo "Breaking changes: add '!' after type/scope (e.g. 'feat!: ...') or a 'BREAKING CHANGE:' footer."
  exit 1
fi

echo "All commit messages follow Conventional Commits."
