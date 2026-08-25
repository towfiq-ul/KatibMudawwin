# Contributing

## Branch model

```
<topic branches> -> develop -> master -> release -> (tag + GitHub Release)
```

- **Topic branches** (`feature/…`, `fix/…`, or anything else off `develop`) are where actual work happens. Open a PR into `develop`.
- **`develop`** is the ongoing-integration branch. This is what `install.sh` builds by default.
- **`master`** receives merges from `develop` once that work is considered release-ready. Nothing lands on `master` directly.
- **`release`** receives merges from `master` when it's actually time to cut a release. **Every push to `release` publishes a release** -- see below. Nothing lands on `release` directly, and nothing lands on it except by merging `master` in.
- Tags (`vX.Y.Z`) and GitHub Releases are created automatically by CI, never by hand.

Each arrow above is a PR + merge, not a direct push -- `develop`, `master`, and `release` should all be protected branches (require a PR, require the "Commit message lint" check to pass) once this is pushed to GitHub.

## Commit messages: Conventional Commits

Every commit on a PR into `develop`, `master`, or `release` must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(optional-scope): description
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

This isn't just style -- `.github/workflows/release.yml` parses these prefixes to decide the next version's major/minor/patch bump (`scripts/ci/compute_release.py`), and `.github/workflows/commitlint.yml` blocks any PR containing a commit that doesn't parse.

- The very first release is always **`v0.0.0`**, regardless of commit content. Normal semver bumping starts from the second release onward.
- A `fix:` commit bumps the **patch** version.
- A `feat:` commit bumps the **minor** version.
- A breaking change bumps the **major** version -- mark it either with `!` right after the type/scope (`feat!: drop config.yaml v1 support`) or a `BREAKING CHANGE:` footer in the commit body.
- If a release contains no `feat`/`fix`/breaking commits (e.g. only `docs`/`chore`), it still ships as a **patch** bump -- every push to `release` is a release.

Examples:

```
feat(desktop): add on-demand summarize button
fix(engine): stop VAD from hallucinating on silence
docs: document the branch model
feat!: require config.yaml v2, drop v1 auto-migration
```

## Cutting a release

1. Open a PR merging `develop` into `master` once `develop` is in a release-ready state. Merge it.
2. Open a PR merging `master` into `release`. Merge it.
3. That push triggers `.github/workflows/release.yml`, which:
   - Computes the next `vX.Y.Z` from commits since the last tag (see the bump rule above).
   - Writes that version into `desktop/package.json`, `desktop/src-tauri/Cargo.toml`, `desktop/src-tauri/tauri.conf.json`, and `engine/pyproject.toml` (`scripts/ci/set_version.py`) so the built packages' own version metadata matches the tag -- these files are never hand-edited or committed back; CI patches them fresh on every release.
   - Runs `make bundle` to build the `.deb`/`.rpm`/AppImage.
   - Creates the git tag and a GitHub Release with generated release notes (grouped by commit type) and the three packages attached.

No manual version bumping, changelog editing, or tagging -- all of it is derived from the commit history automatically.
