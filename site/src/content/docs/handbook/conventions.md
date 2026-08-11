---
title: Conventions
description: The 52 declared fields and what each governs, declared-empty semantics, and what happens on an undeclared root.
sidebar:
  order: 3
---

A record repo's declaration is one JSON file carrying `"schema":
"record-index-conventions/1"` and **52 required fields**.

**Conventions are a full declaration, not overrides.** There is deliberately no "if the repo
did not say, use the first repo's value" branch in `conventions.py`. Every field is
required, absence is an error that names the field, and the error is raised **at load time**
rather than surfacing as an empty table six steps later.

The counterpart is `mechanism.py`: **defaults with overrides**, each value annotated at its
site with the corpus and month it was calibrated on. *You must declare what your repo means;
you may inherit how the search is tuned.*

The required list is written out explicitly in the source rather than derived from a sample
declaration, because a schema derived from one repo's file is that repo's file wearing a
schema's clothes.

## The fields

### `repo` — identity

| Field | Governs |
|---|---|
| `repo.name` | The record's name, printed by the tool and carried in the certificate |
| `repo.db_rel` | Where the index lives, relative to the record root |
| `repo.db_env` | The environment variable that selects an index. A **db selector** — it never names a corpus |

### `markers` — how a root is recognised

`markers` is the list of paths that must all exist for a directory to *be* this record's
root. **Two, not one**, in both fixture repos: an ordinary filename like `CLAUDE.md` is
carried by many directories, and a single-marker resolver would bind some other repo
entirely and then fail deeper in.

### `corpora` — which files are the record

| Field | Governs |
|---|---|
| `corpora.experiments_dir` | The directory the ruling / kickoff globs walk |
| `corpora.record_roots` | Directory roots walked for markdown. A declared root that is not a directory is reported as `declared-but-absent` |
| `corpora.record_top_files` | Individual top-level files that are part of the record |
| `corpora.law_files` | Files parsed for laws |
| `corpora.prose_files` | Files parsed for prose sections |
| `corpora.profile_files` | A profiles registry, if the repo has one |
| `corpora.experiments_table` | A single document carrying an experiments table |
| `corpora.sweep_extra_files` | Extra files the claims sweep reads beyond the record itself |
| `corpora.sweep_extra_dirs` | Extra directories, same |

### `discovery` — which document is which

| Field | Governs |
|---|---|
| `discovery.ruling_doc` | The filename pattern that makes a document a ruling document |
| `discovery.kickoff_doc` | The same for kickoff / handoff documents |
| `discovery.ruling_arc` | How an **arc label** is derived from a ruling filename — `{"strip_from": "ruling"}` or `{"leading": true}` |
| `discovery.kickoff_arc` | The same rule for kickoffs, and it is **deliberately allowed to be the other one** |
| `discovery.experiment_prefix` | How the `experiment` grouping key is read off a filename |
| `discovery.experiment_file` | Which filenames are experiment documents |
| `discovery.spec_file_fragments` | Filename fragments identifying a spec |
| `discovery.report_file_fragment` | The fragment identifying a report |
| `discovery.topical_ruling_files` | Ruling documents that live outside the glob, named individually |

**Arc is identity; experiment is grouping.** `arc` is part of the `rulings` primary key.
Keyed on an `E`-number prefix alone, facet's `E10-ruling.md` (rulings 1–12) and
`E10-offsurface-ruling.md` (rulings 1–7) both become arc `E10` and **collide on seven
primary keys**, and `build()` raises `IntegrityError`. That collision was measured before it
was ruled on. `experiment` — the prefix, a non-key column — serves the grouping the prefix
was attractive for, and costs nothing because it is in no key.

The two fixture repos disagree here on purpose:

```python
alpha_conv.arc_of_ruling_doc("E02-offsurface-ruling.md")  # "E02-offsurface"
beta_conv.arc_of_ruling_doc("E02-offsurface-ruling.md")   # "E02"
```

Same input, two declared rules, two answers — which is the property that makes the rule a
declaration rather than a default.

### `headers` — what opens a block

| Field | Governs |
|---|---|
| `headers.ruling` | **A list** of header patterns that open a ruling |
| `headers.addenda` | A list, for addenda headers |
| `headers.amendment` | A list, for amendment headers |
| `headers.handoff` | A list, for session-handoff headers |
| `headers.sub_ruling` | The marker opening a sub-ruling |
| `headers.sub_closure` | The marker opening a sub-closure |

`headers.ruling` is a list because a shared tool that hard-codes one ruling-header form
breaks on the third repo as surely as on the second — and the convention is plural in
practice. `beta` declares both `^## Decision (\d+)\b(.*)$` and `^## (\d+)\. RULING\b(.*)$`,
and one of its documents carries both. Every pattern's contract is the same: group 1 is the
number, group 2 is the tail. `headers.ruling` may never be empty: a record with no
ruling-header form declared can carry no rulings, which is a declaration error rather than
an empty table.

### `vocabularies` — the words this repo uses

| Field | Governs |
|---|---|
| `vocabularies.verdicts` | The verdict words. `alpha` says ACCEPTED / REJECTED / RATIFIED / WITHDRAWN / FALSIFIED / CLOSED; `beta` says UPHELD / OVERTURNED / SHIPPED |
| `vocabularies.authority` | `{pattern, named, default}` — how a holding's authority is recognised and what it is called |
| `vocabularies.experiment_status` | The status words an experiment can carry |
| `vocabularies.status_words` | `(name, pattern)` pairs for status detection |
| `vocabularies.artifact_kinds` | Extension → kind map |
| `vocabularies.artifact_extensions` | Which extensions make a token an artifact mention |
| `vocabularies.phenomenon_markers` | `(name, pattern)` pairs for phenomena |
| `vocabularies.supersede_verbs` | The verbs that mean one ruling replaced another |

Every vocabulary **reports what it did not recognise**. That is not decoration: running one
repo's parsers against a second record found three loud failures — a missing file raises and
stops the build — and two silent ones nobody had predicted. The law corpus parsed 38 rows
and left `paid_for_by` NULL on every one, because the declared pattern matched an arc range
that repo does not use; and six artifact mentions were dropped (`.mp4` ×3 and `.mkv` ×3) in
the repo whose entire product is video, because the extension map had no video entry.

**And the counter has to be able to move.** Each vocabulary declares a *probe* — a pattern
describing what an input of its kind looks like. The probe defines the population, and
`unrecognised` counts inputs *inside that population* that matched no entry. Counting "every
ruling that named no phenomenon" would read in the hundreds on a healthy record and mean
nothing.

The probe for verdicts is the **announcing form** — `is ACCEPTED`, `is RATIFIED` — narrowed
once more to past participles. The first draft was `\b[A-Z]{4,}\b`, and its first run against
a real record reported **824** unrecognised "verdicts" — ADJUDICATED, BASELINE, OWNER, PASS,
SEAM, WHITE — which are capitalised words in prose and not verdicts at all. The blind spot
this buys is stated rather than hidden: a declared verdict that is not a participle (facet
declares `VOID`) sits outside the population, so its holdings are neither hit nor miss. That
is a limit of the **counter**, not of the parser.

**Report, never gate.** `verify` surfaces these counts and does not fail on them. Which
unrecognised inputs matter is a judgement about a record, not a property of one, and a
diagnostic and a gate are different objects.

### `laws`

`laws.paid_for_by` — the pattern that attributes a law to the arc that paid for it. May be
declared empty.

### `sweep` — the staleness sweep's map of the repo

| Field | Governs |
|---|---|
| `sweep.current_state_files` | Files that describe the repo as it is now |
| `sweep.current_state_dirs` | Directory prefixes, same |
| `sweep.historical_dirs` | Directory prefixes whose documents are history, not current state |
| `sweep.bannered` | A document split by a staleness banner — above it is current, below it is historical |
| `sweep.banner` | The banner pattern |
| `sweep.split_at_release` | A document split at a release marker instead |
| `sweep.current_state_extra` | Per-file overrides, with the reason as the value |
| `sweep.historical_extra` | The same, the other way |
| `sweep.self_reference_exclude` | Path fragments the sweep must not read as claims about the record — a document that quotes counts about itself |
| `sweep.claim_families` | `(label, kind, unit, pattern)` — the phrasings this repo uses for a count claim |

### `verify` — what the gates check

| Field | Governs |
|---|---|
| `verify.count_checks` | `(name, file, pattern, table, where)` — grep the markdown, compare against the database |
| `verify.sequences` | `(arc, kind, lo, hi)` — a declared numbered range, checked for gaps |
| `verify.handoff_coverage` | An arc's handoff range and the numbers legitimately missing from it |
| `verify.experiment_coverage` | The experiment id range that must be present |
| `verify.seeded` | `(question, phrase, target)` — the seeded question set leg 4 runs |

The `seeded` **shape is preserved, not normalised**: a target is a bare `(file, anchor)`
tuple for the ordinary one-target case and a *list* of them where a question legitimately
has several. Callers unpack the bare form directly, so wrapping every target in a list to
make one loop tidier is a change to a public surface — it broke three tests that had bound
to the original shape. Normalising happens where the loop is.

## Declared-empty semantics

Declaring a corpus **empty** is a statement. Leaving the key **out** is not. Only one of
those is a declaration, so the two are treated differently:

- A field **absent** from the document is always an error naming the field.
- A field **present but empty** is an error *unless* it is one of the **21** fields on the
  `MAY_BE_EMPTY` list.

The 21 that may be declared empty: `corpora.prose_files`, `corpora.profile_files`,
`corpora.sweep_extra_files`, `corpora.sweep_extra_dirs`, `corpora.experiments_table`,
`discovery.topical_ruling_files`, `discovery.spec_file_fragments`, `laws.paid_for_by`,
`sweep.current_state_extra`, `sweep.historical_extra`, `sweep.self_reference_exclude`,
`sweep.bannered`, `sweep.split_at_release`, `verify.count_checks`, `verify.sequences`,
`verify.handoff_coverage`, `verify.experiment_coverage`, `verify.seeded`,
`vocabularies.phenomenon_markers`, `headers.addenda`, `headers.amendment`.

The other **31 may not be empty** — and four of them arguably should be. See [known
defects](/record-index/handbook/known-defects/).

## The declaration audits itself

`verify` prints a `[declaration]` section reporting **both directions**:

- **declared-but-absent** — a file or root the declaration names that is not on disk.
- **undeclared-but-present** — a markdown file the walk found that is on no declared list
  and under no declared root prefix.

Only reporting both makes a declaration auditable. A declaration that can report what it
named and not what it missed is the hard-coded-list defect wearing a different hat. This
section is a **diagnostic** and gates nothing.

## What happens on a root with no declaration

Two different failures, and the distinction is load-bearing.

**An unresolvable root is a legal state.** `bind` returns a binding whose `root` is `None`
and whose conventions object answers only the three fields that describe the *command* —
name, `db_rel`, `db_env`. Every field that describes a *document* raises `RootNotFound`, and
the message names the field and names the way out (`--db`). An installed copy with no corpus
beside it must still answer `--help` and still run `q --db <path>`, because the env var and
the `--db` flag select an index and never a corpus. A first draft raised at import and took
both of those down — at the one moment a user is most likely to be running the thing for the
first time.

**A resolved root carrying no declaration is a refusal, at import.** If the markers are
found but the conventions file is not there, `bind` raises `ConventionsError` — out of the
consuming adapter's *import*. The message names the file it looked for:

> no conventions declaration at `<path>`. A record repo declares what its documents mean;
> this tool supplies no default for that.

Through the CLI contract, `ConventionsError` reaches the operator as `REFUSED` with exit
code **4**, and the hint says to state the missing field in the repo's own
`conventions.json`, because this tool ships no default for what a document *means*.
