# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-08-11

The extraction version. Nothing is published to PyPI at this tag; `release.yml` publishes
via OIDC Trusted Publishing when a GitHub release is created, and nothing publishes on push.

### Added

- **The record index, extracted from
  [`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet)**, where every
  convention in it was paid for. It extracts rather than forks: facet's own law book records
  five hand-copies of one function living under four names, invisible to a name-based grep
  for months, and forking thousands of lines into a second repo is that error with three
  more zeros.

  The extraction condition was stated in advance and gated on a measurement — *the index
  extracts when a second repo adopts the conventions* — and
  [`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) is that
  repo.

  **Gated on the way in by byte-identity with facet's in-tree build: 19/19, with zero
  row-level differences on the same corpus.** Two consumers run on it: facet, whose ~2,462
  in-tree lines became a declaration plus an adapter with ~140 of its tests exercising the
  package through it; and armature, whose own index seeded 15/15 with 47 rulings.

- **Conventions as a full declaration.** A record repo declares what its documents mean —
  markers, corpus roots, ruling and kickoff discovery, both arc rules, header forms,
  vocabularies, the staleness sweep's map, and the verify gates — across **52 required
  fields**. Absence is an error at load time that names the field. There is deliberately no
  "if the repo did not say, use the first repo's value" branch: an overrides model ships one
  repo's history as every other repo's silent default.

- **Mechanism as defaults with overrides**, in a separate module, with **every tuning value
  annotated at its site with the corpus and month it was calibrated on**. You must declare
  what your repo means; you may inherit how the search is tuned.

- **Four-leg `verify`** — determinism (byte-identity, with a pre-registered `.dump`
  fallback), counts against the record's own numbering, zero dangling pointers across seven
  tables plus the FTS index, and a seeded question set. Plus two sections printed with the
  word DIAGNOSTIC on them: the declaration audit (both directions — declared-but-absent and
  undeclared-but-present) and the vocabulary report.

- **Vocabularies that report what they did not recognise**, each with a probe defining its
  population so the counter can move. An empty table and a table that silently discarded six
  artifacts are indistinguishable at the call site, and only one of them is correct.

- **`build_and_certify` as one verb**, and the certificate paired to the bytes it describes:
  the index's size and sha256, a per-file manifest of the corpus, the verify transcript, and
  the verify's exit code persisted as a field. `health()` reports SERVING / STALE /
  INDEX_MISSING / INDEX_VERIFY_FAILED / INDEX_NEVER_VERIFIED. Staleness warns rather than
  refuses, because bounded staleness is the normal state of a fresh clone.

- **An exit-code contract** — 0 ok, 1 the operator's invocation was wrong, 2 the tool broke
  on something it did not expect, 3 declared and deliberately unused, 4 the tool ran
  correctly and is telling you not to proceed. Failures reach the operator as a structured
  report (`kind` / `message` / `cause` / `hint`), never a raw stack; `--debug` restores the
  traceback and is presentation only.

- **A suite of 455 checks** across all ten modules, run in CI on Python 3.11 and 3.13, built
  on **two fixture record-repos that disagree on every declarable axis** — markers, corpus
  root, the word for a ruling, both arc rules, verdict vocabulary, header forms, and the
  location of the declaration itself. A suite with one fixture repo cannot tell a declared
  convention from a hard-coded one, because every value would be right for the same reason.

- **A public site and handbook** under `site/`, deployed to GitHub Pages, carrying the same
  numbers and the same four defects that are in this file.

### Known defects — four, pinned in-tree as `xfail(strict=True)`

Reproduced rather than hidden, and paired with ordinary tests that pin the current behaviour
with a number attached. None affects the two current consumers.

1. **`verify()` doubles its diagnostic counts.** `verify()` passes one `Record` to both of
   leg 1's builds, so the two REPORT-ONLY sections report exactly twice the corpus's counts.
   Every gating leg reads the database and is unaffected, and the run still exits 0.
2. **The claim-arc pattern assumes `E`-numbered arcs.** `claims.ARC_RE` is the module
   constant `\bE(\d\d)\b`, hard-coded, while every other arc-shaped value is declared. A repo
   whose arcs are `A01`/`A02` can attribute no count claim to any arc.
3. **The sub-ruling locator is not derived from the declared header form.**
   `headers.sub_ruling` is declared, but the locator is built as the literal
   `'**%s%s '`, so a repo declaring any other marker gets rows whose locator does not occur
   in its own file — and verify leg 3 reports them as dangling pointers produced by the tool.
   Same for `sub_closure`.
4. **Four fields refuse declared-emptiness.** `sweep.current_state_dirs`,
   `sweep.historical_dirs`, `headers.handoff` and `vocabularies.supersede_verbs` are outside
   `MAY_BE_EMPTY`, so a repo whose honest answer is *none* must instead declare a value that
   matches nothing. Both fixture repos carry a directory they would otherwise not have, for
   this reason.

### The contract this version fixes

- **Dependencies: none.** `sqlite3` + `re` + `json`, all stdlib — a declared property, not
  an accident, asserted from both ends: against the project metadata, and by walking every
  module's import statements against a thirteen-name allow-list.
- **Python `>=3.11`**, with CI running the floor and the ceiling and nothing between them.
- **No console script ships.** The command a record repo runs is named after that repo, so
  the entry point belongs to the consumer and this package supplies the contract it runs
  under.

[0.1.0]: https://github.com/mcp-tool-shop-org/record-index/releases/tag/v0.1.0
