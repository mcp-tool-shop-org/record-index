---
title: Verify and the certificate
description: The four legs, the certificate pairing, the exit-code contract as implemented, and the health() states.
sidebar:
  order: 4
---

An index is only worth reading if something checks it against the record it claims to
describe. `verify` is that check. It **builds from the record and never writes the index it
is checking** — the index under test is opened read-and-never-written, and the suite pins
that its bytes are unchanged by a verify.

## The four legs

Legs 1–4 **gate**. Everything after them is printed with the word DIAGNOSTIC on it.

### Leg 1 — determinism

Two builds from an unchanged record, compared **byte for byte**. Determinism is a contract
rather than an aspiration, so everything that could vary is pinned: every traversal is
`sorted()`, every insert order is fixed, the whole build is one transaction, and no
timestamp or random value is ever written.

If byte-identity fails, a **pre-registered fallback** compares the two databases' `.dump`
output — logical determinism — and the transcript prints the first differing byte offset and
then names which leg held: `byte-identity` or `.dump-identity (pre-registered fallback)`. If
neither holds, the leg fails.

The two temporary databases are written to **per-process unique** paths in the same
directory. Two verifies in one working copy once wrote the same two fixed files and could
read each other's bytes mid-build; the collision is now impossible by construction rather
than retried on sight.

### The corpus sections

Between legs 1 and 2 the transcript prints every ruling document and every kickoff document
the sorted glob discovered, with its arc and its row count, so a document that matched
nothing prints as `0 rows - prose only` rather than vanishing. These sections also carry a
gate: a row in the database whose file the glob does **not** discover is an orphan, and it
fails the run.

### Leg 2 — counts against the record's own numbering

Three checks, all declared:

- **`verify.count_checks`** — the verifier greps the markdown with the declared pattern and
  compares that count against a `SELECT COUNT(*)` with the declared `WHERE`. A mismatch
  fails.
- **`verify.sequences`** — a declared numbered range is checked for gaps. Ranges are
  **as declared, not as measured**: a record carrying numbers *above* the declared bound
  prints a completeness note and the bound stays as declared, rather than silently widening
  the gate. (An earlier version editorialised about a document it does not read, and was
  true when written and false eight hours later.)
- **`verify.handoff_coverage`** and **`verify.experiment_coverage`** — a declared range with
  the numbers legitimately missing from it named in advance. A missing number that was not
  pre-registered fails.

### Leg 3 — zero dangling pointers

Every row in all seven tables — `rulings`, `laws`, `experiments`, `handoffs`, `artifacts`,
`phenomena`, `decisions` — plus every row of the FTS index must name a file that exists and
carry a **locator string that occurs inside it**.

Anchors come in two forms and that is deliberate. `anchor` is the human label a session
reads and cites ("Ruling 25c"); `locator` is the exact string findable in the file
(`**25c —`), because GitHub mints anchors for `#`-headings only and a bold lead is not one.
**The dangling-pointer gate checks `locator`**; the query output prints `anchor`. This is
the leg that catches a pointer the *tool* invented — see the sub-ruling locator defect on
[known defects](/record-index/handbook/known-defects/).

### Leg 4 — the seeded question set

The repo declares questions, each with a search phrase and the file-and-anchor that should
answer it. The gate is that the target lands **within the top N** (default 3). A miss prints
the rows that came back instead, so a failure is actionable rather than just red.

## The two diagnostic sections

Printed after leg 4, labelled REPORT ONLY, and they **fail nothing**:

- **`[declaration]`** — corpora declared vs corpora present, in both directions.
- **`[vocabulary]`** — what each declared vocabulary did not recognise, with the
  unrecognised tokens named. A count nobody can act on is a count everybody learns to
  ignore. The block closes with the mechanism's calibration note, so a quoted number carries
  its provenance.

⚑ **These two sections currently report exactly double the corpus's counts.** It is measured,
pinned, and does not touch any gating leg — see [known
defects](/record-index/handbook/known-defects/).

## The transcript is a contract

Other tools parse `verify`'s output, and **the last non-empty line is the verdict**.
Anything added to the transcript is printed *before* the verdict block, and a test pins
that.

The verdict block is:

```
determinism leg that held: byte-identity
VERIFY PASSED - all four legs
```

or, on failure, `VERIFY FAILED - <n>` followed by one `X <reason>` line per failure.

The console's encoding is kept and only its errors handler is relaxed to
`backslashreplace`. The loud half of what this tool prints is the **record**, not its own
prose, and a record carries characters cp1252 cannot encode — a verifier whose failure
report cannot print is a check that cannot fail.

## The certificate

**A build without its verify is the ungated state the certificate exists to close.** In the
repo this was extracted from, `build` and `verify` were separate verbs, and a fresh database
could sit beside a stale certificate indefinitely, reading as verified.

So `build_and_certify` is **one verb**: it builds, verifies in-process, and writes the
certificate from that verify's own transcript and exit code. There is no path here that
writes a database without writing a certificate for it.

```python
from record_index import certificate
certificate.build_and_certify(BINDING, db_path)
```

The certificate is JSON written to `<db_path>.cert.json`, carrying:

| Field | What it is for |
|---|---|
| `schema` | `record-index-certificate/1` |
| `state` | `PASSED` or `FAILED` |
| `verify_exit_code` | The verify's own code, **persisted** — so a caller reads a field rather than a shell's `$?` that nobody kept |
| `db.bytes`, `db.sha256` | The identity of the artifact this certificate describes |
| `corpus.files`, `corpus.id`, `corpus.manifest` | Per-file sha256 of every markdown file the index reads, plus one order-independent digest over the whole manifest |
| `transcript` | The verify transcript, line by line |
| `verified_utc`, `repo`, `verb`, `written_by` | Provenance |

The db digest is what makes "verified" a property of **the bytes present** rather than of a
file having once existed. The corpus manifest is what makes staleness *measurable* rather
than guessed — the comparison names **what moved**, because a warning a session cannot act
on is a warning it learns to ignore.

**Dual-accept on read.** The writer emits exactly one schema id. The reader also accepts the
pre-extraction id `facet-record-index-certificate/1`, so a certificate written before the
rename keeps verifying instead of turning a working index into `INDEX_NEVER_VERIFIED` on
upgrade.

## `health()` — the states

`certificate.health(binding, db_path)` returns `{"state", "serving", "why", ...}`. It is
cheap: one small file, plus a digest of the corpus.

| State | `serving` | When |
|---|---|---|
| `SERVING` | `true` | Certificate present, readable, `PASSED`, describes *this* index, and the corpus digest still matches |
| `STALE` | `true` | Everything above except the corpus moved since the build. Also returns `moved` (up to 12 named paths) and `moved_total` |
| `INDEX_MISSING` | `false` | No index at that path |
| `INDEX_VERIFY_FAILED` | `false` | The certificate records a failed verify |
| `INDEX_NEVER_VERIFIED` | `false` | **Three different causes**, collapsed into one state — see below |

**STALE warns rather than refuses, on purpose.** The database commits at session boundaries,
not every fold, so bounded staleness is the ruled-normal state of a fresh clone, and a
refusal there would fire on correct work.

⚑ **`INDEX_NEVER_VERIFIED` is returned for three distinct conditions**: no certificate
beside the index; a certificate that is unreadable, is not an object, is missing one of the
four required keys, or carries an unknown schema; and a certificate whose recorded digest
does not match the index actually on disk. The `why` string distinguishes them and the suite
pins each one separately, but the **state name does not**. Pinned as an observation on
[known defects](/record-index/handbook/known-defects/).

## The exit-code contract

Measured through a subprocess before this shape existed — twenty rows, two commands. The
surface was inverted at **both** ends against the standard registry (2 for the user, 1 for
the runtime), and **three distinct outcome classes shared exit 1**: a mistyped flag, a
failing verify leg, and a fired gate. A caller could not tell "fix your command" from "do
not trust this index."

| Code | Meaning |
|---|---|
| `0` | ok |
| `1` | the operator's invocation was wrong |
| `2` | the tool broke on something it did not expect |
| `3` | declared and **deliberately unused** — no verb has a partial-completion path, and a code is not populated by inventing a path for it to describe |
| `4` | the tool ran correctly and is telling you not to proceed |

**Four is one code, not two, deliberately**: a failing verify and a fired ANDON both mean the
tool worked and the answer is no. Splitting 4 later is additive and cheap; merging two codes
later is not.

Failures reach the operator as a **structured report**, never a raw stack:

```
<prog>: GATE_FIRED
  message: ANDON: 2 file(s) carry a session-handoff header ...
  cause:   AssertionError
  hint:    this is a gate refusing, not a defect in the tool. Fix what it
           names; there is no flag that skips it
```

The kinds are `GATE_FIRED` (exit 4), `REFUSED` (exit 4 — a `ConventionsError` or a
`RootNotFound`), and `RUNTIME_ERROR` (exit 2). `--debug` adds the traceback and is
**presentation only**: it changes nothing about what runs, skips no gate, and no check
consults it.

`run_contract` wraps `main()` itself rather than the `if __name__ == "__main__"` guard,
because an installed console script calls the function directly — a contract living in the
guard would be present in a source-tree run and absent from every installed command.
`argparse`'s usage-error exit is moved from 2 to 1; only `error()` is overridden, because
`--help` reaches the operator through `exit(0)` and an override there would move a success
onto a failure code.
