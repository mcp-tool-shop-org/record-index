# record-index

A governed SQLite+FTS5 map over a markdown decision record, so a session can **query**
the record instead of reading it — and then read the forty lines the query pointed at
rather than the six hundred it would have skimmed.

The markdown stays canonical. The index is derived, regenerated on every fold, gated by a
four-leg `verify`, and **wrong by definition the day it is hand-edited**.

## Status — SCAFFOLD ONLY

**No tool code is in this repo yet.** This commit exists to satisfy the repo-first rule
(repo exists · `origin` correct · default branch `main` · scaffold pushed **before** any
tool code). The extraction that fills it is halted on a gate — see below.

## Where this comes from

This is an extraction of the record index built and hardened in
[`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet), which is where
every convention below was paid for. It extracts rather than forks because facet's own law
book records five hand-copies of one function living under four names, invisible to a
name-based grep for months; forking thousands of lines into a second repo is that error
with three more zeros.

The extraction condition was stated in advance and gated on measurement: *the index
extracts when a second repo adopts the conventions.*
[`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) is that repo.

## The design, in one paragraph

A record repo declares **what its documents mean** — which files carry rulings, which
header forms open one, what its verdict vocabulary is, which corpora it has. The tool
supplies **how the search works** — parsing, ranking, determinism, the verify legs — with
tuning values that carry the corpus and date they were calibrated on. Conventions are a
**full declaration** (a repo states its own meaning; it never inherits another repo's
history by omission). Mechanism is **defaults with overrides**.

Every vocabulary reports what it **did not recognise**. An empty table and a table that
silently discarded six artifacts are indistinguishable at the call site, and only one of
them is correct.

## Why the build is halted

The classification step measured facet's parsers against armature's record and the
extraction was re-specified from what it found. One item of that re-specification —
deriving a document's arc from its leading `E\d\d` prefix — was measured against facet
before it was built and **collides on 7 primary keys**: `E10-ruling.md` and
`E10-offsurface-ruling.md` both become arc `E10` and their rulings 1–7 are the same key.

The evidence, and the interaction with the ruling-header item that makes the two jointly
fatal on armature as well, are reported in `armature/docs/dispatches/`. Nothing is built on
it until it is ruled.

## Licence

MIT — see [LICENSE](LICENSE).
