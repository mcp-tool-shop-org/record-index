---
title: The record-index handbook
description: What record-index is, where it comes from, and the design in one paragraph.
sidebar:
  order: 1
---

**Query the record instead of reading it.**

`record-index` is a governed SQLite+FTS5 map over a markdown decision record. It parses a
repo's own documents into tables — rulings, laws, experiments, handoffs, artifacts,
phenomena, decisions — with a full-text index over them, so a session can ask a question
and then read the forty lines the answer pointed at rather than the six hundred it would
have skimmed.

The markdown stays canonical. The index is **derived**, regenerated on every fold, gated by
a four-leg `verify`, and **wrong by definition the day it is hand-edited**.

## The design, in one paragraph

A record repo declares **what its documents mean** — which files carry rulings, which header
forms open one, what its verdict vocabulary is, which corpora it has. The tool supplies
**how the search works** — parsing, ranking, determinism, the verify legs — with tuning
values that carry the corpus and date they were calibrated on. Conventions are a **full
declaration**: a repo states its own meaning, and never inherits another repo's history by
omission. Mechanism is **defaults with overrides**.

There is deliberately no "if the repo did not say, use the first repo's value" branch
anywhere in `conventions.py`. An overrides model ships one repo's history as every other
repo's silent default, and a second repo then inherits a first repo's past by omission —
which is the exact defect the extraction was halted to fix.

## Where it comes from

This is an **extraction** of the record index built and hardened in
[`mcp-tool-shop-org/facet`](https://github.com/mcp-tool-shop-org/facet), which is where
every convention here was paid for.

It extracts rather than forks because facet's own law book records five hand-copies of one
function living under four names, invisible to a name-based grep for months. Forking
thousands of lines into a second repo is that error with three more zeros.

The extraction condition was stated in advance and gated on a measurement: *the index
extracts when a second repo adopts the conventions.*
[`mcp-tool-shop-org/armature`](https://github.com/mcp-tool-shop-org/armature) is that repo,
and it is the second consumer.

## Where it is

| | As of 2026-08-11 |
|---|---|
| Checks in the suite | 455 — 451 passing, 4 pinned as `xfail(strict=True)` |
| Interpreters in CI | 3.11 and 3.13 |
| Runtime dependencies | 0 — `sqlite3` + `re` + `json`, all stdlib |
| Consumers | 2 — facet and armature |
| Known defects | 4, reproduced and pinned in-tree |
| On PyPI | **Not yet** |

`release.yml` publishes via OIDC Trusted Publishing when a GitHub release is created;
nothing publishes on push.

## Why a second fixture repo exists

The suite is built on **two** fixture record-repos, `alpha` and `beta`, and the second is
not a copy. They disagree on the markers, the corpus root, the word for a ruling, both arc
rules, the verdict vocabulary, the authority word, the artifact extensions, the phrasing
families, the header forms, and the location of the declaration file itself.

A suite with one fixture repo cannot tell a declared convention from a hard-coded one,
because every value would be right for the same reason. Three of the four known defects on
the [known defects](/record-index/handbook/known-defects/) page are hard-coded values that
`beta` found and `alpha` never could.

## The rest of this handbook

- [Getting started](/record-index/handbook/getting-started/) — install, declare, build,
  verify, and the adapter a consuming repo writes.
- [Conventions](/record-index/handbook/conventions/) — the declaration fields, what each
  governs, declared-empty semantics, and what happens on an undeclared root.
- [Verify and the certificate](/record-index/handbook/verify-and-certificate/) — the four
  legs, the pairing, the exit-code contract, and the `health()` states.
- [Known defects](/record-index/handbook/known-defects/) — four pinned defects and three
  pinned observations, quoted from the tests that hold them.

The canonical copies live in the repo:
[README](https://github.com/mcp-tool-shop-org/record-index/blob/main/README.md) ·
[source](https://github.com/mcp-tool-shop-org/record-index/tree/main/record_index) ·
[suite](https://github.com/mcp-tool-shop-org/record-index/tree/main/tests).
Where this handbook and the repo disagree, the repo is right — it is what the tests run
against.
