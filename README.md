<p align="center">
  <a href="README.ja.md">日本語</a> | <a href="README.zh.md">中文</a> | <a href="README.es.md">Español</a> | <a href="README.fr.md">Français</a> | <a href="README.hi.md">हिन्दी</a> | <a href="README.it.md">Italiano</a> | <a href="README.pt-BR.md">Português (BR)</a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/mcp-tool-shop-org/record-index/main/docs/assets/logo-wide.png" alt="record-index — query the record instead of reading it" width="820">
</p>

# record-index

<p align="center">
  <a href="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml"><img src="https://github.com/mcp-tool-shop-org/record-index/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://mcp-tool-shop-org.github.io/record-index/"><img src="https://img.shields.io/badge/landing%20page-live-2ea043" alt="Landing page"></a>
</p>

A governed SQLite+FTS5 map over a markdown decision record, so a session can **query**
the record instead of reading it — and then read the forty lines the query pointed at
rather than the six hundred it would have skimmed.

**[Landing page & handbook →](https://mcp-tool-shop-org.github.io/record-index/)**

The markdown stays canonical. The index is derived, regenerated on every fold, gated by a
four-leg `verify`, and **wrong by definition the day it is hand-edited**.

## Status — extracted, tested, not yet on PyPI

*(This section read "SCAFFOLD ONLY — no tool code is in this repo yet" until 2026-08-11,
which the extraction landing falsified. Corrected in place.)*

**The extraction landed.** The package is on `main`, gated on the way in by byte-identity
with facet's in-tree build (19/19) and **zero row-level differences** on the same corpus.
Two consumers run on it: [facet](https://github.com/mcp-tool-shop-org/facet), whose ~2,462
in-tree lines became a declaration plus an adapter with ~140 of its tests exercising the
package through it, and [armature](https://github.com/mcp-tool-shop-org/armature), whose
own index seeded 15/15 with 47 rulings.

**The package carries its own suite: 455 checks** across all ten modules, run in CI on
Python 3.11 and 3.13, built on two fixture record-repos that disagree on every declarable
axis — markers, corpus roots, arc rules, verdict vocabulary, header forms — so a wrong
implementation has somewhere to become visible. **Dependencies: none.** Stdlib only
(`sqlite3` + `re` + `json`), and that is a declared property, not an accident.

**Four defects are known, reproduced, and pinned in-tree as `xfail(strict=True)` tests**
rather than hidden: `verify()` doubles its diagnostic counts (gating legs unaffected); the
claim-arc pattern assumes `E`-numbered arcs; the sub-ruling locator is not derived from the
declared header form; and four declaration fields cannot be declared honestly empty. None
affects the two current consumers; all four are queued for the next version.

**Not yet on PyPI.** `release.yml` publishes via OIDC Trusted Publishing when a GitHub
release is created; nothing publishes on push.

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

## The halt that used to be here, and how it ended

*(Until 2026-08-11 this section halted the build on a measured collision. The halt was
real, the ruling came, and the build proceeded — kept here as the trail rather than
deleted.)*

The classification step had measured that deriving a document's arc from its leading
`E\d\d` prefix **collides on 7 primary keys** against facet (`E10-ruling.md` and
`E10-offsurface-ruling.md` both become arc `E10`). The executor caught it against a test
whose name records the same failure, the joint ruling was withdrawn and re-derived, and
the extraction proceeded through its gates. The trail — evidence, the overturned answers,
and the ruling that replaced them — is in `armature/docs/dispatches/` (the S02 arc).

## Licence

MIT — see [LICENSE](LICENSE).
