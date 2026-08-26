# Releasing

This repo follows a governed branch/release model. Read this before opening a
PR or cutting a release.

## Branch Types

### Feature branches - `DEV/<name>/<description>`

Use for new features and non-trivial enhancements.

**Examples:** `DEV/brennan/resize-workflow`, `DEV/alex/pdf-tables`

Target: always open PRs against the current `REL/v*.*.*` branch, never directly
against `master`.

### Bug branches - `BUG/<name>/<description>`

Use for fixing a regression, or a fix on a release branch too substantial for
a direct commit (see [Direct Push Rules](#direct-push-rules) below).

**Examples:** `BUG/brennan/aspect-ratio-lock`, `BUG/alex/toc-page-break`

Target: open PRs against the current `REL/v*.*.*` branch.

### Release branches - `REL/v<major>.<minor>.<patch>`

Created when preparing a release. The version follows [SemVer](https://semver.org/):
`MAJOR.MINOR.PATCH`.

**Examples:** `REL/v2.0.0`, `REL/v2.1.0`, `REL/v3.0.0`

Source: branch off `master` (or the previous release branch, if stacking).
Target: merge into `master` via PR once all requirements below are met.

## Branch Flow

```
master
  └── REL/v*.*.*
        ├── DEV/<name>/<description>   (feature work -> PR -> REL)
        └── BUG/<name>/<description>   (fixes         -> PR -> REL)
              ↓ PR (after full testing)
           master
```

## Direct Push Rules

### `master` - no direct pushes, ever

All changes to `master` arrive via a `REL/v*.*.*` -> `master` PR, with CI
passing and required reviews approved. A Claude Code hook
(`.claude/scripts/main-guard.sh`) blocks file edits while checked out on
`master` as a local safety net for this rule.

### `REL/v*.*.*` - limited direct commits allowed

Direct commits to a release branch are permitted **only** for:
- Minor fixes surfaced during testing (small, localized changes)
- Documentation updates
- Version number bumps

If a required change is substantial, open a `BUG/<name>/<description>` branch
off the release branch and merge it back via PR instead.

## PR Requirements

| PR type | Requirements |
|---|---|
| `DEV/**` -> `REL/**` | CI passing (`ci-feature.yml`), code review approved |
| `BUG/**` -> `REL/**` | CI passing (`ci-feature.yml`), code review approved |
| `REL/**` -> `master` | CI passing (`ci-release.yml`), code review approved, full test suite passing on that exact commit |

> Full testing on the release commit means: after any last direct commits to
> the release branch (minor fixes, version bump, docs), re-run the complete
> test suite and confirm it passes before requesting the merge to `master`.
> Do not merge on a stale test run.

## Versioning

**`VERSION.txt` (repo root, a bare version string like `2.0.0`) is the
definitive source of truth for CI** - it's what the workflows below read to
derive the release tag. **`.claude-plugin/plugin.json`'s `version` field must
be kept in sync with it** - that's the field Claude Code itself reads (e.g.
for `/plugin list`), but nothing in CI derives tags from it directly. Bump
both together on the release branch before opening the `REL/v*.*.*` ->
`master` PR.

`ci-release.yml` verifies, on every `REL/**` -> `master` PR, that:
1. The version tag derived from `VERSION.txt` is not already taken - the PR
   cannot merge if the version hasn't been bumped past the last released tag.
2. `VERSION.txt` and `.claude-plugin/plugin.json`'s `version` field match.

When that PR merges, every push to `master` triggers `release.yml`: it
resolves the tag from `VERSION.txt` (skipping if that tag already exists, so
non-release pushes to `master` are a no-op), creates a draft GitHub Release,
and publishes it. Publishing runs under the `release` GitHub Environment,
which requires a human reviewer's approval before it executes - so pushing to
`master` starts the release, but a person still has to approve the publish
step. Do not create version tags manually.

Version increments are determined by changes to the **markdown syntax and
YAML front matter authors write** - the actual interface between a Dilon
document author and this tooling:

- **MAJOR** - a breaking change. Existing Dilon markdown documents must be
  rewritten (front-matter shape, marker syntax, heading conventions) to
  compile correctly against this release.
- **MINOR** - a backward-compatible addition. Existing documents still
  compile unchanged, but authors now have new markers/skills/capabilities
  available to adopt.
- **PATCH** - a bug fix. No new markers, no removed markers, no front-matter
  changes. Documents that already compiled correctly still compile the same
  way, just without the bug.

**Decision razor:** imagine a Dilon document already written against the
current syntax. Ask:
- Would this release require *rewriting* that document to compile? -> **MAJOR**
- Would this release let the author *add* new markers/features to it, but it
  still compiles unchanged as-is? -> **MINOR**
- Would this release require *no changes* to that document at all? -> **PATCH**

## What's Deliberately Not Here

This repo adapts the `nav3-repo-template` governance pattern but drops the
pieces specific to firmware/hardware repos, since there's no analog here:
Docker/devcontainer image builds, SBOM generation, and the ISO-62304
`verification/test-catalog.md` traceability catalog. CI runs the three Python
test suites (`tests/run_tests.py`, `tests/run_form_tests.py`,
`tests/run_extractor_tests.py`) directly instead.
