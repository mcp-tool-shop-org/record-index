# record-index: how it works

Mapped at 2026-09-25 from commit a9a84a2.

## What this is

6 parts, mostly Python (26 files), TypeScript (2) and JavaScript (1). Work enters through 3 doors; the busiest is CI, which reaches 2 parts. It publishes to PyPI.

## What changed since the last map

This is the first map.

## What comes in

1. **CI.** On a pull request touching 5 paths; on a push touching 5 paths; or by hand. Runs tests/.
2. **pages.** On a push to main touching 2 paths; or by hand. Runs site/astro.config.mjs and site/src/.
3. **Release.** When a release is published. Checks record_index/.

## What happens through CI

1. The workflow runs tests/ in tests.
2. That reaches record_index (6 files).

## Who reads the results

CI writes nothing this map can see.

## The other doors

**pages** runs site/astro.config.mjs and site/src/, and deploys the site.

**Release** checks record_index/ and publishes to PyPI.

## What breaks what

- **record_index** is imported only from tests, by 1 part (tests), and sits on the path of 2 doors.

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

People write .github/, docs/, the repository root and site/; 1 write with a path built at run time may land here.

## Where to start

.github/workflows/ci.yml → record_index/__init__.py → record_index/conventions.py

Read those in order to follow one pull request end to end.

## What this map cannot see

- 1 import could not be resolved: `tests/test_packaging.py` imports a path built at run time.
- 1 write and 4 reads use paths built at run time and are not named here.
- Statistics confidence is low: fewer than 30 qualifying commits in the window, and fewer than 20 source files reach 10 revisions.

Regenerate with `npx --yes @dogfood-lab/atlas map`.
