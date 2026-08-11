---
title: Getting started
description: Install, declare your repo's conventions, build, verify, and write the four-line adapter.
sidebar:
  order: 2
---

## Install

```bash
pip install record-index
```

⚑ **Not yet, as of 2026-08-11.** The package is on `main` and tested in CI, and nothing has
been published to PyPI. `release.yml` publishes via OIDC Trusted Publishing when a GitHub
release is created; nothing publishes on push. Until that release exists, the working path
is the source:

```bash
git clone https://github.com/mcp-tool-shop-org/record-index
cd record-index
pip install -e .
python -m pytest tests -q     # 451 passed, 4 xfailed
```

Python **3.11 or newer**. **No dependencies** — the index is `sqlite3` + `re` + `json`, all
standard library. That is a declared property rather than an accident: a consuming repo
installs one package and inherits no transitive surface, and the suite asserts it from both
ends — once against the project metadata, once by walking every module's import statements
against an allow-list of thirteen stdlib names.

## 1 — Declare what your documents mean

Your repo writes one JSON file. Its location is up to you; both fixture repos in this
package's suite keep it somewhere different, because the path is a parameter of `bind` and
not a constant.

```json
{
  "schema": "record-index-conventions/1",
  "repo": {
    "name": "beta",
    "db_rel": "index/beta.db",
    "db_env": "BETA_INDEX_DB"
  },
  "markers": ["LAWS.md", "record/arcs"],
  "corpora": {
    "experiments_dir": "record/arcs",
    "record_roots": ["."],
    "record_top_files": ["LAWS.md", "OVERVIEW.md"],
    "law_files": ["LAWS.md"],
    "prose_files": [],
    "...": "..."
  },
  "headers": {
    "ruling": ["^## Decision (\\d+)\\b(.*)$", "^## (\\d+)\\. RULING\\b(.*)$"],
    "addenda": [],
    "...": "..."
  }
}
```

**52 fields are required**, and absence is an error at load time that names the field.
The full list and what each governs is on the
[conventions](/record-index/handbook/conventions/) page.

Note `headers.ruling` is a **list**. A shared tool that hard-codes one ruling-header form
breaks on the third repo as surely as on the second, and the convention is plural in
practice — armature's early ruling documents write `## N. RULING —` and its closing ones
write `## Ruling N`.

## 2 — Write the adapter

**No console script ships with this package, deliberately.** The command a record repo runs
is named after that repo — `facet-index`, not `record-index` — so the entry point belongs to
the consumer. This package supplies the contract it runs under.

The adapter is four lines plus a `main`:

```python
import record_index
from record_index import cli as _cli

BINDING = record_index.bind(__file__)
globals().update(BINDING.exports())


def main(argv=None):
    return _cli.run_contract(lambda a: _cli.main(BINDING, a), argv,
                             db_env=BINDING.conv.db_env)


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

`bind(__file__)` takes the adapter's own path, so a source checkout resolves exactly as it
always did: the adapter lives at `<root>/tools/<name>.py`, and its parent's parent is the
root. `bind` also accepts `conventions_rel`, `root`, `name`, `db_rel` and `db_env` when your
layout differs.

`exports()` returns the module-level names your adapter re-exports — the exit codes, the
declared patterns, the parse verbs, the generic text mechanism. They are **named
explicitly** rather than swept from `dir()`: an adapter's surface is a contract other tools
and tests bind to, and a surface derived from whatever happened to be public is not one.

### How `bind` resolves a root

By **testing for it**, never by assuming. The markers your declaration names are looked for
in the module's parent directory and then in the working directory, in that order — most
specific first. There is deliberately **no walk up** from the working directory: that would
resolve a subdirectory of a checkout, and could also reach a parent that is a different
record.

Two markers, not one, and the second is not decoration. `CLAUDE.md` alone is an ordinary
filename and many directories carry one; a single-marker resolver would bind a working
directory that is some other repo entirely and then fail deeper in.

A resolver that cannot find a corpus **refuses** — it does not return a plausible-looking
directory. But an unresolvable root is a **legal state**, not an import error: an installed
copy with no corpus beside it must still answer `--help` and still run `q --db <path>`,
because the env var and the `--db` flag select an *index* and never a *corpus*. The refusal
is deferred to the first thing that actually needs a document.

## 3 — Build, verify, query

The adapter exposes four verbs:

```bash
python tools/beta_index.py build
python tools/beta_index.py verify
python tools/beta_index.py q "dangling pointers"
python tools/beta_index.py claims
```

`--db` selects the index to work against; `$BETA_INDEX_DB` (whatever you declared as
`repo.db_env`) does the same. Precedence: an explicit `--db` wins over the env var, which
wins over the record's own tracked index.

From Python, the same verbs hang off the binding:

```python
B = record_index.bind(__file__)
B.build(B.db_default())
B.verify(B.db_default())          # returns 0 or 4
B.claims(B.db_default())
```

And to build with the certificate in one step — which is the shape to prefer:

```python
from record_index import certificate

certificate.build_and_certify(B, B.db_default())
certificate.health(B, B.db_default())     # {"state": "SERVING", ...}
```

Why one verb: `build` and `verify` as separate verbs let a fresh database sit beside a stale
certificate indefinitely, reading as verified. That was measured the hard way in the repo
this came from. See [verify and the
certificate](/record-index/handbook/verify-and-certificate/).

## 4 — Commit the pair

A record repo commits its **database and its certificate together**, or neither. This repo
builds neither and its `.gitignore` excludes `*.db` and `*.cert.json` for that reason — the
pair belongs to the repo whose record it describes.
