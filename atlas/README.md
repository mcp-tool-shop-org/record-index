# record-index: how it works

Mapped at 2026-09-30 from commit 2c20d4b by Atlas 1.24.0.

## What this is

6 parts, mostly Python (26 files), CSS (2), TypeScript (2), Astro (1) and JavaScript (1). Work enters through 4 doors; the busiest is CI, which reaches 2 parts. It publishes to PyPI. It deploys a site to GitHub Pages. People import record_index.

## What changed since 2026-09-25 (a9a84a2)

- CI's pull request trigger now also names `codecov.yml`.
- CI's push trigger now also names `codecov.yml`.
- record_index (pyproject.toml) is a new package. It loads record_index/__init__.py.
- 1 file added and 1 changed content, across 2 parts.

## What comes in

1. **CI.** On a pull request touching 6 paths; on a push touching 6 paths; or by hand. Runs tests/.
2. **pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
3. **Release.** When a release is published. Checks record_index/.
4. **record_index** (the package people import). Loads record_index/__init__.py.

## What happens through CI

1. The workflow runs tests/ in tests.
2. That reaches record_index (10 files).
3. It uploads coverage to Codecov.

## Who reads the results

CI writes nothing this map can see.

## The other doors

**pages** runs site/astro.config.mjs and site/src/, and deploys the site.

**Release** checks record_index/ and publishes to PyPI.

**record_index** (the package people import) loads record_index/__init__.py.

## What breaks what

- **record_index** is imported only from tests, by 1 part (tests), and sits on the path of 3 doors.

## What tends to change together

No two source files changed together often enough to name.

Window: 180 days; a pair counts from 3 shared commits, since the window holds fewer than 30 qualifying commits.

## What no test touches

Every code part is imported by at least one test.

## Written but never read

No place this map can see is written, so none goes unread.

## Helpers that look duplicated

No two parts export a helper that looks alike.

## Generated, never hand-edited

Nothing in this repository writes to a tracked place this map can see.

## Hand-authored

People write .github/, docs/, the repository root and site/. Nothing in this repository writes to them.

## Where to start

record_index/__init__.py → record_index/conventions.py

Read those in order to follow one import of record_index end to end. This path follows record_index (the package people import) from its entry, since CI runs only tests.

## What this map cannot see

- 1 import could not be resolved: `tests/test_packaging.py` imports a path built at run time.
- 1 read uses a path built at run time and is not named here.
- 7 writes and 3 reads go to a path their caller passes, not to this repository.
- Statistics confidence is low: fewer than 30 qualifying commits in the window, and fewer than 25 source files reach 10 revisions.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
