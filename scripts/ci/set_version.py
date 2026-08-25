#!/usr/bin/env python3
"""Writes a version (e.g. "0.1.0", a leading "v" is stripped if present)
into every file that embeds a package version, so the .deb/.rpm/AppImage
`make bundle` is about to build -- and the engine's own package version --
match the git tag release.yml is creating. Called right after
compute_release.py, before `make bundle`.

The git tag (derived from commit history, see compute_release.py) is the
single source of truth for the version. These files are just build
inputs that need to agree with it at build time -- this script isn't run
outside CI, and its edits are never committed back.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# path -> (pattern matching exactly the package's own version field, replacement template)
FILES: dict[str, tuple[re.Pattern[str], str]] = {
    "desktop/package.json": (re.compile(r'("version":\s*")[^"]+(")'), r"\g<1>{v}\g<2>"),
    "desktop/src-tauri/Cargo.toml": (re.compile(r'^(version = ")[^"]+(")', re.MULTILINE), r"\g<1>{v}\g<2>"),
    "desktop/src-tauri/tauri.conf.json": (re.compile(r'("version":\s*")[^"]+(")'), r"\g<1>{v}\g<2>"),
    "engine/pyproject.toml": (re.compile(r'^(version = ")[^"]+(")', re.MULTILINE), r"\g<1>{v}\g<2>"),
}


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: set_version.py X.Y.Z", file=sys.stderr)
        sys.exit(1)
    version = sys.argv[1].lstrip("v")

    for rel_path, (pattern, template) in FILES.items():
        path = REPO_ROOT / rel_path
        text = path.read_text(encoding="utf-8")
        new_text, count = pattern.subn(template.format(v=version), text, count=1)
        if count != 1:
            print(f"error: no version field matched in {rel_path}", file=sys.stderr)
            sys.exit(1)
        path.write_text(new_text, encoding="utf-8")
        print(f"{rel_path}: version -> {version}")


if __name__ == "__main__":
    main()
