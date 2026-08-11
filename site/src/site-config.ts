import type { DefaultSiteConfig } from '@mcptoolshop/site-theme';

// Every claim on this page traces to code in record_index/, to a test in tests/,
// or to README.md in this repo — or it says plainly that it has not happened yet.
// The counters are dated because they are measurements, not properties.

const REPO = 'https://github.com/mcp-tool-shop-org/record-index';

export const config: DefaultSiteConfig = {
  template: 'default',
  title: 'record-index — query the record instead of reading it',
  description:
    'A governed SQLite+FTS5 map over a markdown decision record. Per-repo conventions are declared, never inherited; the mechanism is supplied. Four-leg verify, certificate-paired, stdlib only.',
  logoBadge: 'RI',
  brandName: 'record-index',
  repoUrl: REPO,
  footerText:
    'MIT Licensed — built by <a href="https://github.com/mcp-tool-shop-org" style="color:var(--color-muted);text-decoration:underline">mcp-tool-shop-org</a>. Counters on this page are dated; the repo carries the live ones.',

  hero: {
    badge: '455 checks · 2 consumers · stdlib only · 4 known defects, pinned',
    headline: 'Query the record',
    headlineAccent: 'instead of reading it.',
    description:
      'A governed SQLite+FTS5 map over a markdown decision record, so a session reads the forty lines the query pointed at rather than the six hundred it would have skimmed.<br><br>The markdown stays canonical. The index is <strong>derived</strong>, regenerated on every fold, gated by a four-leg <code>verify</code>, and <strong>wrong by definition the day it is hand-edited</strong>.',
    primaryCta: { href: 'handbook/', label: 'Read the handbook' },
    secondaryCta: { href: REPO, label: 'The source' },
    previews: [
      {
        label: 'A repo declares what its documents mean',
        code: 'docs/index/conventions.json\n  52 required fields',
      },
      {
        label: 'A consumer binds in four lines',
        code: 'B = record_index.bind(__file__)\nglobals().update(B.exports())',
      },
      {
        label: 'Then asks the record',
        code: 'q "dangling pointers"\nverify   # four legs, all must pass',
      },
    ],
  },

  sections: [
    {
      kind: 'features',
      id: 'what-it-does',
      title: 'What it does',
      features: [
        {
          title: 'The record becomes queryable',
          desc: 'Rulings, laws, experiments, handoffs, artifacts, phenomena and decisions are parsed out of a repo\'s own markdown into SQLite with an FTS5 index over it. Every row carries the file, the line, a human anchor to cite, and a locator string findable in the source.',
        },
        {
          title: 'Conventions are declared, not guessed',
          desc: 'Which files carry rulings, which header forms open one, what the verdict vocabulary is, which corpora exist — a repo states all of it. There is no "if the repo did not say, use the first repo\'s value" branch anywhere in conventions.py, on purpose: that branch ships one repo\'s history as every other repo\'s silent default.',
        },
        {
          title: 'Every vocabulary reports what it dropped',
          desc: 'An empty table and a table that silently discarded six artifacts are indistinguishable at the call site, and only one of them is correct. Each vocabulary declares a probe defining its population, and counts the inputs inside it that matched no entry — reported, never gating.',
        },
      ],
    },

    {
      kind: 'data-table',
      id: 'numbers',
      title: 'The numbers, as measured',
      subtitle:
        'Measured on 2026-08-11 against the tree at that date, not estimated. Where something has not happened, the row says so rather than being left off.',
      columns: ['Counter', 'As of 2026-08-11'],
      rows: [
        ['Checks in the suite', '455 — 451 passing, 4 pinned as xfail(strict=True)'],
        [
          'Interpreters in CI',
          '3.11 and 3.13 — the floor requires-python declares and the ceiling the classifiers claim, and nothing between them',
        ],
        [
          'Runtime dependencies',
          '0. sqlite3 + re + json, all stdlib — asserted twice, once against the project metadata and once by walking every module\'s import statements',
        ],
        ['Modules', '10, pinned by name so one added to the tree and not to the distribution is visible'],
        [
          'Fixture record-repos',
          '2 — alpha and beta, disagreeing on the markers, the corpus root, the word for a ruling, both arc rules, the verdict vocabulary, the header forms and the location of the declaration itself',
        ],
        ['Declared conventions fields', '52 required; 21 of them may be declared empty, 31 may not'],
        [
          'Consumers',
          '2 — facet, whose ~2,462 in-tree lines became a declaration plus an adapter, and armature, whose own index seeded 15/15 with 47 rulings',
        ],
        ['Known defects', '4, reproduced and pinned in-tree as strict-xfail tests rather than hidden'],
        [
          'On PyPI',
          'Not yet. release.yml publishes via OIDC Trusted Publishing when a GitHub release is created; nothing publishes on push',
        ],
      ],
    },

    {
      kind: 'features',
      id: 'declared-vs-supplied',
      title: 'What you declare, what the tool supplies',
      subtitle:
        'The whole design fits in one sentence: you must declare what your repo MEANS; you may inherit how the search is TUNED.',
      features: [
        {
          title: 'A repo declares its meaning — in full',
          desc: 'Every one of the 52 fields is required. Absence is an error that names the field and is raised at load time, rather than surfacing as an empty table six steps later. A repo states its own meaning; it never inherits another repo\'s history by omission.',
        },
        {
          title: 'The tool supplies the mechanism',
          desc: 'Parsing, ranking, determinism, the verify legs. Nobody adopting this has evidence to tune BM25 with, and inviting them to turn knobs they cannot evaluate is worse than a default.',
        },
        {
          title: 'Every tuning value carries its calibration',
          desc: 'bm25(8.0, 1.0), 400 candidates, 3 phrase slots — each annotated at the site with the corpus and month it was fit on. That is the difference between a default and a number somebody once measured somewhere: a reader who wants to know whether 400 means anything for their record can see that it does not yet.',
        },
        {
          title: 'Arc is identity; experiment is grouping',
          desc: 'The schema says both rather than picking one, because keying on the E-number alone collides on seven primary keys against a real corpus where one experiment ran two ruling series. That collision was measured before it was ruled on, and the extraction halted until it was.',
        },
      ],
    },

    {
      kind: 'features',
      id: 'verify',
      title: 'Four legs, and a certificate that names the bytes',
      subtitle:
        'Legs 1–4 gate; the declaration audit and the vocabulary report are printed with the word DIAGNOSTIC on them, because which unrecognised inputs matter is a judgement about a record and not a property of one.',
      features: [
        {
          title: '1 — Determinism',
          desc: 'Two builds from an unchanged record, compared byte for byte, with a pre-registered .dump-identity fallback for the case where SQLite\'s own file header defeats byte equality. The transcript names which leg held.',
        },
        {
          title: '2 — Counts against the record\'s own numbering',
          desc: 'Declared count checks grep the markdown and compare against the database; declared sequences report gaps in a numbered range. A record carrying more than a declared bound prints a completeness note — the bound stays as declared rather than silently widening.',
        },
        {
          title: '3 — Zero dangling pointers',
          desc: 'Every row in all seven tables plus the FTS index must name a file that exists and a locator string that occurs inside it. This is the leg that catches a pointer the tool invented.',
        },
        {
          title: '4 — The seeded question set',
          desc: 'A set of questions declared by the repo, each with the file and anchor that should answer it. The gate is that the target lands within the top N; a miss prints what came back instead.',
        },
        {
          title: 'The certificate is written by the same verb',
          desc: 'build_and_certify builds, verifies in-process, and writes the certificate from that verify\'s own transcript and exit code. There is no path that writes a database without writing a certificate for it — because build and verify as separate verbs let a fresh database sit beside a stale certificate indefinitely, reading as verified.',
        },
        {
          title: 'Staleness warns; it does not refuse',
          desc: 'The certificate carries the index\'s size and digest and a per-file manifest of the corpus, so a certificate found beside a different index is detected rather than trusted. A corpus that has moved since the build reports STALE and keeps serving, because bounded staleness is the normal state of a fresh clone.',
        },
      ],
    },

    {
      kind: 'data-table',
      id: 'not-solved',
      title: 'What is not solved',
      subtitle:
        'Four defects, each reproduced and pinned in the suite as an xfail(strict=True) test — which means the day one is fixed, the suite fails until this page and that test are both updated. None affects the two current consumers. A page that only lists wins is not a status report.',
      columns: ['Defect', 'Measured', 'Where'],
      rows: [
        [
          'verify() reports its diagnostic counts twice',
          'On alpha, one build reports verdicts 4/3, artifact kinds 5/1, law paid_for_by 2/1, experiment status 2/1, phenomenon markers 1/2, ruling headers 6/0, 8 total unrecognised and 1 declaration finding. The transcript reports 8/6, 10/2, 4/2, 4/2, 2/4, 12/0, 16, and the same finding listed twice — exactly double, every row.',
          'index.py — Record.record() hands back a fresh Record per call precisely so counters do not accumulate, but verify() passes one Record to both of leg 1\'s builds. The accumulation is in the two REPORT-ONLY sections; every gating leg reads the database and is unaffected, and the run still exits 0.',
        ],
        [
          'The claim-arc pattern assumes E-numbered arcs',
          'On beta, whose arcs are A01 and A02, both declared-family sites land in the unparseable list with "no arc attributable on this line", the STALE count is 0, and the claim that one of its own documents is wrong by five is never made.',
          'claims.py — ARC_RE is the module constant \\bE(\\d\\d)\\b, hard-coded from the repo this was extracted from, while every other arc-shaped value in the package is declared. measurements() carries the same assumption in CAST(substr(id,2) AS INTEGER).',
        ],
        [
          'The sub-ruling locator is not derived from the declared header form',
          'With headers.sub_ruling declared as ^\\*\\*(\\d+)\\.([a-z])\\s+[—–-] and the document written **1.a — , the row\'s locator comes out **1a , which does not occur in that document. Verify leg 3 then reports dangling pointers produced by the tool rather than by the record.',
          'parse.py — the locator is built as the literal \'**%s%s \' % (num, letter), the form of the repo this was extracted from. Same for sub_closure.',
        ],
        [
          'Four fields refuse declared-emptiness',
          'sweep.current_state_dirs, sweep.historical_dirs, headers.handoff and vocabularies.supersede_verbs are not in MAY_BE_EMPTY, so a repo whose honest answer is "none" cannot say so — the loader refuses []. Both fixture repos carry a directory they would otherwise not have, for exactly this reason.',
          'conventions.py — the file\'s own law is that declaring a corpus empty is a statement where omitting the key is not, and MAY_BE_EMPTY grants that to 21 fields. These four are outside it.',
        ],
      ],
    },

    {
      kind: 'code-cards',
      id: 'surface',
      title: 'The surface a consumer takes on',
      subtitle:
        'No console script ships with this package, deliberately: the command a record repo runs is named after that repo, so the entry point belongs to the consumer and this package supplies the contract it runs under.',
      cards: [
        {
          title: 'The adapter a consuming repo writes',
          code: 'import record_index\nfrom record_index import cli as _cli\n\nBINDING = record_index.bind(__file__)\nglobals().update(BINDING.exports())\n\n\ndef main(argv=None):\n    return _cli.run_contract(\n        lambda a: _cli.main(BINDING, a), argv,\n        db_env=BINDING.conv.db_env)',
        },
        {
          title: 'The exit-code contract it runs under',
          code: '0  ok\n1  the operator\'s invocation was wrong\n2  the tool broke on something it did\n   not expect\n3  declared and DELIBERATELY UNUSED —\n   no verb has a partial-completion\n   path, and a code is not populated\n   by inventing a path for it\n4  the tool ran correctly and is\n   telling you not to proceed',
        },
      ],
    },
  ],
};
