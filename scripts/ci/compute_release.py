#!/usr/bin/env python3
"""Computes the next semantic version + release notes for a push to the
`release` branch (see .github/workflows/release.yml), from Conventional
Commits since the last vX.Y.Z tag.

No tag yet -> baseline is v0.0.0. Bump rule: any breaking change (a '!'
after type/scope, or a 'BREAKING CHANGE:' footer) -> major; else any
'feat:' -> minor; else any 'fix:' -> patch; else -> patch (every push to
`release` is a release, so an all-chores/docs push still ships a patch
bump rather than being silently skipped).

Writes `tag` and `notes_file` to $GITHUB_OUTPUT (falls back to stdout when
run outside CI) for the workflow's later steps to use.
"""

from __future__ import annotations

import os
import re
import subprocess

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
SUBJECT_PATTERN = re.compile(
    r"^(?P<type>feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)"
    r"(?:\([^)]+\))?(?P<breaking>!)?: (?P<desc>.+)$"
)
TYPE_LABELS = {
    "feat": "Features",
    "fix": "Fixes",
    "perf": "Performance",
    "refactor": "Refactoring",
    "docs": "Documentation",
    "build": "Build",
    "ci": "CI",
    "chore": "Chores",
    "test": "Tests",
    "style": "Style",
    "revert": "Reverts",
}
SECTION_ORDER = [
    "Features", "Fixes", "Performance", "Refactoring", "Documentation",
    "Build", "CI", "Chores", "Tests", "Style", "Reverts", "Other",
]


def last_tag() -> tuple[int, int, int] | None:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*.[0-9]*.[0-9]*"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    m = TAG_PATTERN.match(result.stdout.strip())
    return tuple(int(x) for x in m.groups()) if m else None  # type: ignore[return-value]


def commits_since(tag: tuple[int, int, int] | None) -> list[tuple[str, str, str]]:
    rev_range = f"v{tag[0]}.{tag[1]}.{tag[2]}..HEAD" if tag else "HEAD"
    log = subprocess.run(
        ["git", "log", "--no-merges", "--format=%H%x1f%s%x1f%b%x1e", rev_range],
        capture_output=True, text=True, check=True,
    ).stdout
    commits = []
    for chunk in log.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        sha, subject, body = chunk.split("\x1f")
        commits.append((sha, subject.strip(), body.strip()))
    return commits


def classify(commits: list[tuple[str, str, str]]) -> tuple[str, dict[str, list[str]]]:
    bump = "patch"  # default: every push to `release` ships, even if nothing parses
    bump_rank = {"patch": 0, "minor": 1, "major": 2}
    grouped: dict[str, list[str]] = {}
    for sha, subject, body in commits:
        m = SUBJECT_PATTERN.match(subject)
        if not m:
            grouped.setdefault("Other", []).append(f"{subject} ({sha[:7]})")
            continue
        type_ = m.group("type")
        breaking = bool(m.group("breaking")) or "BREAKING CHANGE" in body
        label = TYPE_LABELS.get(type_, "Other")
        grouped.setdefault(label, []).append(f"{m.group('desc')} ({sha[:7]})")
        candidate = "major" if breaking else ("minor" if type_ == "feat" else "patch")
        if bump_rank[candidate] > bump_rank[bump]:
            bump = candidate
    return bump, grouped


def bump_version(base: tuple[int, int, int], kind: str) -> tuple[int, int, int]:
    major, minor, patch = base
    if kind == "major":
        return (major + 1, 0, 0)
    if kind == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def main() -> None:
    base_tag = last_tag()
    base = base_tag or (0, 0, 0)
    commits = commits_since(base_tag)
    kind, grouped = classify(commits)
    new = bump_version(base, kind)
    tag = f"v{new[0]}.{new[1]}.{new[2]}"

    notes_path = "RELEASE_NOTES.md"
    with open(notes_path, "w", encoding="utf-8") as f:
        f.write(f"# {tag}\n\n")
        if not commits:
            f.write("No changes recorded since the last release.\n")
        for label in SECTION_ORDER:
            items = grouped.get(label)
            if not items:
                continue
            f.write(f"## {label}\n\n")
            for item in items:
                f.write(f"- {item}\n")
            f.write("\n")

    gh_output = os.environ.get("GITHUB_OUTPUT")
    lines = [f"tag={tag}", f"notes_file={notes_path}"]
    if gh_output:
        with open(gh_output, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))


if __name__ == "__main__":
    main()
