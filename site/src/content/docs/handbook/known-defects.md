---
title: Known defects
description: Four defects pinned as strict-xfail tests, and three behaviours pinned as measured rather than as approved.
sidebar:
  order: 5
---

Four defects are known, reproduced, and pinned in-tree as `xfail(strict=True)` tests rather
than hidden. **Strict** matters: the day one is fixed, the suite fails until the test and
this page are both updated. A defect that quietly starts passing is a defect nobody
finds out was fixed.

Each is paired with a second, ordinary test that pins the *current* behaviour with a number
attached — so the finding carries evidence, and a change to it is visible in the suite
rather than only in prose.

**None of the four affects the two current consumers.** Three of them are values hard-coded
from the repo this package was extracted from, and all three were found by `beta`, the
second fixture record-repo — which is the entire reason a second fixture exists.

---

## 1 — `verify()` doubles its diagnostic counts

`Record.record()` hands back a **fresh** `Record` per call precisely so that vocabulary
counters and corpus findings do not accumulate across builds; the docstring names *`verify`
builds three times in one process* as the reason. But `verify()` itself passes **one**
`Record` to both of leg 1's builds, so every number in the transcript's two diagnostic
sections is exactly **double** the corpus's real count.

Measured on `alpha`:

| Vocabulary | One build (recognised / unrecognised) | What `verify` prints |
|---|---|---|
| verdicts | 4 / 3 | 8 / 6 |
| artifact kinds | 5 / 1 | 10 / 2 |
| law `paid_for_by` | 2 / 1 | 4 / 2 |
| experiment status | 2 / 1 | 4 / 2 |
| phenomenon markers | 1 / 2 | 2 / 4 |
| ruling headers | 6 / 0 | 12 / 0 |
| **total unrecognised** | **8** | **16** |

The declaration audit's `1 finding(s)` likewise prints as `2 finding(s)`, with the same
finding listed twice.

**The gating legs are untouched.** The accumulation is in the two REPORT-ONLY sections;
every gating leg reads the database, and the run still exits `0`. That is pinned as
behaviour, not as a wish: a second test asserts the doubling is *exactly* two and that the
exit code is `EXIT_OK`.

Where: `record_index/index.py`, `verify()`. Tests:
`test_the_transcript_reports_the_corpus_counts_not_twice_the_corpus_counts` (xfail-strict)
and `test_the_doubling_is_exactly_two_and_the_gates_are_untouched_by_it`.

---

## 2 — The claim-arc pattern assumes `E`-numbered arcs

`claims.ARC_RE` is the module constant `\bE(\d\d)\b` — the arc form of the repo this package
was extracted from, **hard-coded**. Every other arc-shaped value in the package is declared:
`discovery.ruling_arc`, `discovery.experiment_prefix`, `sweep.claim_families`,
`laws.paid_for_by`. This one is not, so a repo whose arcs are not `E<dd>` cannot attribute
any count claim to any arc.

Measured on `beta`, whose arcs are `A01` and `A02`:

- Both of its declared-family sites land in the unparseable list with `no arc attributable
  on this line` — `OVERVIEW.md:8 "2 decisions"` and `live/status.md:8 "7 decisions"`.
- `UNPARSEABLE (count-claim-shaped, no family): 2`
- `STALE (current-state documents disagreeing with the record): 0`
- The claim that `live/status.md` is wrong by five is **never made**, and the sweep still
  exits `0`.

`measurements()` carries the same assumption in `CAST(substr(id,2) AS INTEGER)`, which reads
an experiment id as one prefix character plus digits.

Where: `record_index/claims.py`. Tests:
`test_a_repo_whose_arcs_are_not_e_numbered_can_still_attribute_a_claim` (xfail-strict) and
`test_the_arc_pattern_is_the_e_form_and_beta_pays_for_it`.

---

## 3 — The sub-ruling locator is not derived from the declared header form

`headers.sub_ruling` is a **declared convention**, but the locator a sub-ruling row carries
is built in `parse.py` as the literal `'**%s%s ' % (num, letter)` — the alpha/facet form,
hard-coded. A repo that legally declares any other sub-ruling marker therefore gets rows
whose locator string **does not occur in its own file**, and verify leg 3 reports them as
dangling pointers *produced by the tool* rather than by the record.

Evidence: with `headers.sub_ruling` declared as `^\*\*(\d+)\.([a-z])\s+[—–-]` and the
document written `**1.a — `, the row's locator comes out `**1a `, which is absent from the
document.

The same applies to `headers.sub_closure`.

This is the one defect that can make a *gating* leg fail, and it fails it in the worst
direction — leg 3 exists to catch a pointer the tool invented, and here it is doing exactly
its job on a repo that declared its conventions correctly.

Where: `record_index/parse.py`. Test:
`test_a_declared_sub_ruling_marker_produces_a_findable_locator` (xfail-strict).

---

## 4 — Four fields refuse declared-emptiness

`conventions.py`'s own law is that **declaring a corpus empty is a statement where omitting
the key is not** — and `MAY_BE_EMPTY` grants that to `prose_files`, `profile_files` and
nineteen others. It does **not** grant it to:

- `sweep.current_state_dirs`
- `sweep.historical_dirs`
- `headers.handoff`
- `vocabularies.supersede_verbs`

So a repo whose honest answer is *none* for any of those cannot say so: the loader refuses
`[]`, and the repo must instead declare a value that matches nothing.

**Both fixture repos in this suite carry a directory they would otherwise not have, for
exactly this reason** — which is the clearest evidence available that the constraint is
wrong rather than protective.

Where: `record_index/conventions.py`, `MAY_BE_EMPTY`. Test:
`test_a_repo_with_no_current_state_directory_can_declare_that` (xfail-strict).

---

# Pinned as measured, not as approved

Three behaviours are pinned by ordinary tests that say, in their own docstrings, that they
record what the tool *does* rather than what it *should* do. They are not defects and not
endorsements; they are the places where a reader should know the answer was measured rather
than designed.

## A `count_checks` leg naming an absent file exits 2, not 4

A **declared corpus** that is absent is skipped and reported — that is the ruled behaviour,
and the parse suite covers it. A `verify.count_checks` leg naming an absent file is a
different path: it goes through `rec.lines_of` and raises `FileNotFoundError`, which the CLI
reports as a **runtime error (exit 2)** rather than as a **refusal (exit 4)**.

Measured through a subprocess: `rc == EXIT_RUNTIME`, `RUNTIME_ERROR` and `FileNotFoundError`
both present in stderr, and no raw `Traceback` — the structured report holds. With
`--debug`, the traceback appears and the code stays 2.

Tests: `test_a_count_check_naming_an_absent_file_raises_rather_than_failing_a_leg`,
`test_an_unexpected_break_exits_runtime_through_a_subprocess`.

## A resolved root with no declaration refuses at import time

An **unresolvable root** is a legal state: `bind` returns a binding with `root = None`, the
command surface stays alive, and every field describing a document raises `RootNotFound`
naming the field and naming `--db` as the way out.

A **resolved root carrying no declaration** is a different case, and it raises
`ConventionsError` out of `bind` — which means out of a consuming adapter's *import*. The
refusal names the file it looked for. Through the CLI contract that surfaces as `REFUSED`,
exit 4.

Test: `test_a_resolved_root_with_no_declaration_refuses_at_bind_time`.

## `health()` collapses three conditions into `INDEX_NEVER_VERIFIED`

One state name is returned for three distinct situations:

1. **No certificate** beside the index.
2. **An unusable certificate** — unreadable bytes, not a JSON object, missing any of
   `schema` / `state` / `db` / `corpus`, or carrying a schema id the reader does not accept.
3. **A certificate describing a different index** — its recorded `db.sha256` does not match
   the file on disk.

The `why` string distinguishes all three, and the suite pins each separately. The **state
name** does not distinguish them, so a caller branching on `state` alone cannot tell "you
never verified this" from "someone edited the database after you did."

Tests: `test_an_index_with_no_certificate_never_serves`,
`test_an_unreadable_certificate_does_not_serve`,
`test_a_certificate_missing_a_required_key_does_not_serve`,
`test_an_unknown_certificate_schema_does_not_serve`,
`test_a_certificate_beside_a_different_index_is_detected`.
