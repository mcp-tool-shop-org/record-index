"""Schema, build, verify, query, claims, and the console entry point.

DETERMINISM IS A CONTRACT, NOT AN ASPIRATION. Two builds from an unchanged
record must be byte-identical. Everything that could vary is pinned: every
traversal is sorted(), every insert order is fixed, the whole build is ONE
transaction, and no timestamp or random value is ever written. `verify` tests
this rather than trusting it, with a pre-registered `.dump` fallback if SQLite's
own file header defeats byte equality.

ANCHORS COME IN TWO FORMS AND THAT IS DELIBERATE. `anchor` is the human label a
session reads and cites ("Ruling 25c"). `locator` is the exact string findable
in the file ("**25c —"), because GitHub mints anchors for `#`-headings only and
a bold lead is not one. The dangling-pointer gate checks `locator`; the query
output prints `anchor`.

⚑ THE TRANSCRIPT IS A CONTRACT. Other tools parse verify's output into a
certificate, and the LAST NON-EMPTY LINE is the verdict. Anything added to this
transcript is printed BEFORE the verdict block; the vocabulary report added by
the extraction obeys that, and a test in this package pins it.
"""
import os
import re
import sqlite3
import sys

from . import text as T
from .mechanism import DEFAULT
from .parse import Record

EXIT_OK = 0
EXIT_USER = 1          # the operator's invocation was wrong
EXIT_RUNTIME = 2       # the tool broke on something it did not expect
EXIT_PARTIAL = 3       # declared and deliberately unused
EXIT_REFUSED = 4       # the tool ran correctly and is telling you not to proceed


SCHEMA = """
CREATE TABLE rulings (
  arc TEXT NOT NULL, number TEXT NOT NULL, parent TEXT, kind TEXT NOT NULL,
  experiment TEXT,
  date TEXT, verdict TEXT, authority TEXT NOT NULL,
  holding TEXT NOT NULL, file TEXT NOT NULL, anchor TEXT NOT NULL,
  locator TEXT NOT NULL, line INTEGER NOT NULL,
  supersedes TEXT, superseded_by TEXT,
  PRIMARY KEY (arc, number, kind)
) WITHOUT ROWID;

CREATE TABLE laws (
  statement TEXT NOT NULL, kind TEXT NOT NULL, section TEXT, paid_for_by TEXT,
  file TEXT NOT NULL, anchor TEXT NOT NULL, locator TEXT NOT NULL,
  line INTEGER NOT NULL
);

CREATE TABLE experiments (
  id TEXT PRIMARY KEY, question TEXT, status TEXT, verdict TEXT,
  spec_file TEXT, report_file TEXT,
  file TEXT NOT NULL, anchor TEXT NOT NULL, locator TEXT NOT NULL,
  line INTEGER NOT NULL
) WITHOUT ROWID;

CREATE TABLE handoffs (
  arc TEXT NOT NULL, number INTEGER NOT NULL, experiment TEXT,
  date TEXT, outcome TEXT,
  commits TEXT, superseded INTEGER NOT NULL,
  file TEXT NOT NULL, anchor TEXT NOT NULL, locator TEXT NOT NULL,
  line INTEGER NOT NULL,
  PRIMARY KEY (arc, number)
) WITHOUT ROWID;

CREATE TABLE artifacts (
  path TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT, mentions INTEGER NOT NULL,
  provenance_ruling TEXT,
  file TEXT NOT NULL, anchor TEXT NOT NULL, locator TEXT NOT NULL,
  line INTEGER NOT NULL
) WITHOUT ROWID;

CREATE TABLE phenomena (
  name TEXT NOT NULL, marker TEXT NOT NULL, statement TEXT NOT NULL,
  instances TEXT,
  file TEXT NOT NULL, anchor TEXT NOT NULL, locator TEXT NOT NULL,
  line INTEGER NOT NULL
);

CREATE TABLE decisions (
  subject TEXT NOT NULL, tool TEXT NOT NULL, key TEXT NOT NULL,
  value TEXT, status TEXT NOT NULL, ruling TEXT, why TEXT,
  file TEXT NOT NULL, anchor TEXT NOT NULL, locator TEXT NOT NULL,
  line INTEGER NOT NULL,
  PRIMARY KEY (subject, tool, key)
) WITHOUT ROWID;

-- `title` is the SEARCH surface: a concatenation tuned for retrieval. `disp` is
-- what a reader sees. They are separate because optimising one degrades the
-- other: a search title packed with arc and verdict tokens reads as noise.
CREATE VIRTUAL TABLE fts USING fts5(
  title, body,
  tbl UNINDEXED, key UNINDEXED, file UNINDEXED, anchor UNINDEXED,
  locator UNINDEXED, line UNINDEXED, disp UNINDEXED,
  tokenize = 'unicode61 remove_diacritics 2'
);
"""


def build(rec, db_path, quiet=False):
    """Build the index. Returns counts; the Record carries the findings."""
    rulings = rec.parse_rulings()
    rec.link_supersessions(rulings)
    laws = rec.parse_laws()
    experiments = rec.parse_experiments()
    handoffs = rec.parse_handoffs()
    decisions = rec.parse_decisions()
    artifacts = rec.parse_artifacts(rulings)
    phenomena = rec.parse_phenomena(rulings)
    prose = rec.parse_prose({r["file"] for r in rulings})

    d = os.path.dirname(db_path)
    if d and not os.path.isdir(d):
        os.makedirs(d)          # scripts create their own output directories
    if os.path.exists(db_path):
        os.remove(db_path)      # fresh DB each build; never an incremental update

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA page_size=4096")
    con.execute("PRAGMA journal_mode=DELETE")
    con.executescript(SCHEMA)
    fts = []

    def add_fts(tbl, key, title, body, file, anchor, locator, line, disp=None):
        fts.append((title or "", body or "", tbl, key, file, anchor, locator,
                    line, disp if disp is not None else (title or "")))

    with con:
        for r in rulings:
            verdict, authority = rec.classify(r["holding"])
            con.execute(
                "INSERT INTO rulings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r["arc"], r["number"], r["parent"], r["kind"], r["experiment"],
                 r["date"], verdict, authority, r["holding"],
                 r["file"], r["anchor"], r["locator"], r["line"],
                 r["supersedes"], r["superseded_by"]))
            add_fts("rulings", "%s %s" % (r["arc"], r["anchor"]),
                    "%s %s %s %s %s" % (r["arc"], r["anchor"], authority,
                                        verdict or "", r["holding"]),
                    r["body"], r["file"], r["anchor"], r["locator"], r["line"],
                    disp=r["holding"])
        for r in laws:
            con.execute("INSERT INTO laws VALUES (?,?,?,?,?,?,?,?)",
                        (r["statement"], r["kind"], r["section"], r["paid_for_by"],
                         r["file"], r["anchor"], r["locator"], r["line"]))
            add_fts("laws", r["statement"][:60], r["statement"], r["body"],
                    r["file"], r["anchor"], r["locator"], r["line"],
                    disp=r["statement"])
        for r in experiments:
            con.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (r["id"], r["question"], r["status"], r["verdict"],
                         r["spec_file"], r["report_file"],
                         r["file"], r["anchor"], r["locator"], r["line"]))
            add_fts("experiments", r["id"], "%s %s" % (r["id"], r["question"] or ""),
                    r["body"], r["file"], r["anchor"], r["locator"], r["line"],
                    disp=r["question"] or r["status"])
        for r in handoffs:
            con.execute("INSERT INTO handoffs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (r["arc"], r["number"], r["experiment"], r["date"],
                         r["outcome"], r["commits"], r["superseded"],
                         r["file"], r["anchor"], r["locator"], r["line"]))
            add_fts("handoffs", "%s handoff %d" % (r["arc"], r["number"]),
                    "%s handoff %d %s" % (r["arc"], r["number"], r["outcome"]),
                    r["body"], r["file"], r["anchor"], r["locator"], r["line"],
                    disp=r["outcome"])
        for r in artifacts:
            con.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?,?,?,?)",
                        (r["path"], r["kind"], r["status"], r["mentions"],
                         r["provenance_ruling"], r["file"], r["anchor"],
                         r["locator"], r["line"]))
            add_fts("artifacts", r["path"], r["path"], r["body"],
                    r["file"], r["anchor"], r["locator"], r["line"],
                    disp="%s [%s%s] %d mentions"
                         % (r["path"], r["kind"],
                            "/" + r["status"] if r["status"] else "",
                            r["mentions"]))
        for r in phenomena:
            con.execute("INSERT INTO phenomena VALUES (?,?,?,?,?,?,?,?)",
                        (r["name"], r["marker"], r["statement"], r["instances"],
                         r["file"], r["anchor"], r["locator"], r["line"]))
            add_fts("phenomena", r["anchor"], r["statement"], r["body"],
                    r["file"], r["anchor"], r["locator"], r["line"],
                    disp=r["statement"])
        for r in decisions:
            con.execute("INSERT INTO decisions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (r["subject"], r["tool"], r["key"], r["value"],
                         r["status"], r["ruling"], r["why"], r["file"],
                         r["anchor"], r["locator"], r["line"]))
            add_fts("decisions", "%s %s %s" % (r["subject"], r["tool"], r["key"]),
                    "%s %s %s %s" % (r["subject"], r["tool"], r["key"], r["value"]),
                    r["body"], r["file"], r["anchor"], r["locator"], r["line"],
                    disp="%s = %s [%s]" % (r["key"], r["value"], r["status"]))
        for r in prose:
            add_fts("prose", "%s · %s" % (r["file"], r["title"]),
                    r["title"], r["body"], r["file"], r["anchor"],
                    r["locator"], r["line"], disp=r["title"])
        con.executemany(
            "INSERT INTO fts (title, body, tbl, key, file, anchor, locator, line, disp) "
            "VALUES (?,?,?,?,?,?,?,?,?)", fts)
    con.execute("VACUUM")       # fixed final layout, so two builds compare byte-wise
    con.close()

    counts = dict(rulings=len(rulings), laws=len(laws),
                  experiments=len(experiments), handoffs=len(handoffs),
                  artifacts=len(artifacts), phenomena=len(phenomena),
                  decisions=len(decisions), prose_sections=len(prose),
                  fts=len(fts))
    if not quiet:
        print("[build] %s" % db_path)
        for k in sorted(counts):
            print("  %-16s %6d" % (k, counts[k]))
    return counts


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

def query(con, phrase, limit=8, mech=None):
    """Two-stage retrieval: exact phrase first, then bm25 scaled by coverage.

    Why not bm25 alone: a record repeats its vocabulary across arcs, so a
    disjunction ranks a row matching a few common terms alongside one matching
    every term. Why coverage SCALES bm25 rather than overriding it: overriding
    was tried and FALSIFIED - coordination level as primary sort scored 9/14
    against bm25's 12/14, because it discards length normalisation and long
    prose sections trivially contain every term. Ranking by title-coverage first
    scored 11/14. Scaling keeps length normalisation and reached 13/14. Every
    variant is a generic retrieval mechanism; none knows about a document.
    """
    mech = mech or DEFAULT
    sql = ("SELECT file, anchor, disp, line, tbl, "
           "bm25(fts, %s, %s) AS r, title || ' ' || body "
           "FROM fts WHERE fts MATCH ? ORDER BY r, file, line LIMIT ?"
           % (mech.BM25_TITLE_WEIGHT, mech.BM25_BODY_WEIGHT))
    out, seen = [], set()

    # STAGE 1 - the exact adjacent phrase, over the FULL word run with stopwords
    # KEPT, because a phrase is adjacency and dropping "the"/"is" breaks it.
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_.'-]*", phrase)
             if len(w) > 1]
    if len(words) > 1:
        try:
            for f, a, t, line, tbl, r, _ in con.execute(
                    sql, ('"%s"' % " ".join(words), mech.PHRASE_SLOTS)).fetchall():
                if (f, a) not in seen:
                    seen.add((f, a))
                    out.append((f, a, t, line, tbl, r))
        except sqlite3.OperationalError:
            pass

    # STAGE 2 - relaxed: content words OR'd, bm25 scaled by term coverage
    ts = T.fts_terms(phrase)
    try:
        rows = con.execute(
            sql, (" OR ".join('"%s"' % w for w in ts), mech.CANDIDATES)).fetchall()
    except sqlite3.OperationalError:
        return out[:limit]
    scored = []
    for f, a, t, line, tbl, r, hay in rows:
        low = hay.lower()
        cover = sum(1 for w in ts if w in low)
        # bm25 is negative-better; scaling a negative score by a fraction < 1
        # moves it toward zero, i.e. demotes it. Floor at one term.
        scored.append((r * (max(cover, 1) / float(len(ts))), f, line,
                       (f, a, t, line, tbl, r)))
    scored.sort(key=lambda s: (s[0], s[1], s[2]))
    for row in (s[3] for s in scored):
        if (row[0], row[1]) not in seen:
            seen.add((row[0], row[1]))
            out.append(row)
    return out[:limit]


# ---------------------------------------------------------------------------
# verify - four legs, non-zero exit on any failure
# ---------------------------------------------------------------------------

def _grep_count(rec, rel, pattern):
    rx = re.compile(pattern)
    return sum(1 for ln in rec.lines_of(rel) if rx.match(ln))


def _sequence_numbers(con, arc, kind):
    rows = con.execute(
        "SELECT number FROM rulings WHERE arc=? AND kind=?", (arc, kind)).fetchall()
    have = set()
    for (n,) in rows:
        m = re.match(r"^A?(\d+)$", n)
        if m:
            have.add(int(m.group(1)))
    return sorted(have)


def _sequence_gaps(con, arc, kind, lo, hi):
    return sorted(set(range(lo, hi + 1)) - set(_sequence_numbers(con, arc, kind)))


def verify(rec, db_path, top_n=3):
    """The four legs, plus the declaration audit and the vocabulary report.

    Legs 1-4 GATE. The two sections the extraction added are DIAGNOSTICS and are
    printed with that word on them: which unrecognised inputs matter is a
    judgement about a record, not a property of one, and a diagnostic and a gate
    are different objects.
    """
    conv = rec.conv
    fails = []
    print("=" * 78)
    print("record_index verify - four legs")
    print("=" * 78)

    # ---- leg 1: determinism -------------------------------------------------
    # The temp paths are PER-PROCESS unique, same directory: two verifies in one
    # working copy used to write the same two fixed files and could read each
    # other's bytes mid-build. The collision is impossible by construction rather
    # than retried on sight.
    print("\n[leg 1] determinism - two builds from an unchanged record")
    tmp_a = db_path + ".det_a.%d" % os.getpid()
    tmp_b = db_path + ".det_b.%d" % os.getpid()
    build(rec, tmp_a, quiet=True)
    build(rec, tmp_b, quiet=True)
    with open(tmp_a, "rb") as fh:
        ba = fh.read()
    with open(tmp_b, "rb") as fh:
        bb = fh.read()
    if ba == bb:
        print("  BYTE-IDENTICAL   %d bytes, both builds" % len(ba))
        det_leg = "byte-identity"
    else:
        da = "\n".join(sqlite3.connect(tmp_a).iterdump())
        db_ = "\n".join(sqlite3.connect(tmp_b).iterdump())
        if da == db_:
            first = next((i for i in range(min(len(ba), len(bb)))
                          if ba[i] != bb[i]), -1)
            print("  byte-identity FAILED (first differing offset %d of %d/%d bytes)"
                  % (first, len(ba), len(bb)))
            print("  .DUMP-IDENTICAL  %d chars - logical determinism holds" % len(da))
            det_leg = ".dump-identity (pre-registered fallback)"
        else:
            print("  FAIL - neither byte- nor .dump-identical")
            fails.append("determinism: two builds differ logically")
            det_leg = "NEITHER"
    for p in (tmp_a, tmp_b):
        if os.path.exists(p):
            os.remove(p)

    con = sqlite3.connect(db_path)

    # ---- the discovered corpus, printed so the glob's misses are visible ----
    print("\n[corpus] ruling documents discovered by the sorted glob")
    docs = rec.ruling_documents()
    for arc, experiment, rel in docs:
        n = con.execute("SELECT COUNT(*) FROM rulings WHERE file=?",
                        (rel,)).fetchone()[0]
        print("  %-46s arc %-18s %s"
              % (rel.replace(conv.experiments_dir + "/", ""), arc,
                 "%d rows" % n if n else "0 rows - prose only"))
    print("  %d documents matched %s" % (len(docs), conv.ruling_doc_re.pattern))
    indexed = {r[0] for r in con.execute("SELECT DISTINCT file FROM rulings")}
    orphans = sorted(indexed - {rel for _, _, rel in docs})
    if orphans:
        print("  ROWS FROM UNDISCOVERED FILES: %s" % orphans)
        fails.append("rulings from files the glob does not discover: %s" % orphans)

    print("\n[corpus] kickoff documents discovered by the sorted glob")
    kdocs = rec.handoff_documents()
    for arc, experiment, rel in kdocs:
        n = con.execute("SELECT COUNT(*) FROM handoffs WHERE file=?",
                        (rel,)).fetchone()[0]
        print("  %-46s arc %-18s %s"
              % (rel.replace(conv.experiments_dir + "/", ""), arc,
                 "%d rows" % n if n else "0 rows - prose only"))
    print("  %d documents matched %s" % (len(kdocs), conv.kickoff_doc_re.pattern))
    k_indexed = {r[0] for r in con.execute("SELECT DISTINCT file FROM handoffs")}
    k_orphans = sorted(k_indexed - {rel for _, _, rel in kdocs})
    if k_orphans:
        print("  ROWS FROM UNDISCOVERED FILES: %s" % k_orphans)
        fails.append("handoffs from files the glob does not discover: %s" % k_orphans)

    # ---- leg 2: counts against the record's own numbering ------------------
    print("\n[leg 2] counts - the verifier's own grep against the DB")
    for name, rel, pattern, table, where in conv.count_checks:
        g = _grep_count(rec, rel, pattern)
        d = con.execute("SELECT COUNT(*) FROM %s WHERE %s" % (table, where)).fetchone()[0]
        ok = (g == d)
        print("  %-28s grep %4d   db %4d   %s" % (name, g, d, "ok" if ok else "MISMATCH"))
        if not ok:
            fails.append("count %s: grep %d != db %d" % (name, g, d))

    # Ranges as DECLARED, not as measured. They are pre-registered bounds; the
    # record carrying more than a bound prints as a completeness note rather than
    # silently widening the gate.
    for arc, kind, lo, hi in conv.sequences:
        gaps = _sequence_gaps(con, arc, kind, lo, hi)
        print("  %-28s %s %d-%d gaps: %s"
              % (arc + " sequence", kind, lo, hi, gaps if gaps else "none"))
        if gaps:
            fails.append("%s %s sequence gaps %s" % (arc, kind, gaps))
        above = [n for n in _sequence_numbers(con, arc, kind) if n > hi]
        if above:
            # States ONLY what it measured. An earlier version editorialised
            # about a document it does not read, and was true when written and
            # false eight hours later.
            print("  %-28s ABOVE the declared bound of %d: %s  <- measured; the "
                  "bound stays as declared" % ("  ^ completeness", hi, above))

    hc = conv.handoff_coverage
    if hc:
        hg = sorted(r[0] for r in con.execute(
            "SELECT number FROM handoffs WHERE arc=?", (hc["arc"],)).fetchall())
        missing = sorted(set(range(hc["lo"], hc["hi"] + 1)) - set(hg))
        print("  %-28s present %s   missing %s"
              % ("%s handoffs %d-%d" % (hc["arc"], hc["lo"], hc["hi"]), hg,
                 missing if missing else "none"))
        if missing != list(hc["expect_missing"]):
            fails.append("%s handoff coverage unexpected: missing %s"
                         % (hc["arc"], missing))

    ec = conv.experiment_coverage
    if ec:
        exp = sorted(r[0] for r in con.execute("SELECT id FROM experiments").fetchall())
        want = ["%s%02d" % (ec.get("prefix", "E"), i)
                for i in range(ec["lo"], ec["hi"] + 1)]
        miss = [e for e in want if e not in exp]
        print("  %-28s have %d, missing %s"
              % ("experiments %s-%s" % (want[0], want[-1]), len(exp),
                 miss if miss else "none"))
        if miss:
            fails.append("experiments missing %s" % miss)

    # ---- leg 3: zero dangling pointers -------------------------------------
    print("\n[leg 3] pointers - every row's file exists and its locator is findable")
    cache = {}
    dangling = 0
    checked = 0
    for table in ("rulings", "laws", "experiments", "handoffs",
                  "artifacts", "phenomena", "decisions"):
        rows = con.execute("SELECT file, anchor, locator FROM %s" % table).fetchall()
        bad = 0
        for f, a, loc in rows:
            checked += 1
            if f not in cache:
                cache[f] = rec.read(f) if rec.exists(f) else None
            src = cache[f]
            if src is None or loc not in src:
                bad += 1
        dangling += bad
        print("  %-12s %5d rows   dangling %d" % (table, len(rows), bad))
        if bad:
            fails.append("%s: %d dangling pointers" % (table, bad))
    fts_bad = 0
    for f, loc in con.execute("SELECT file, locator FROM fts").fetchall():
        if f not in cache:
            cache[f] = rec.read(f) if rec.exists(f) else None
        if cache[f] is None or loc not in cache[f]:
            fts_bad += 1
    print("  %-12s %5d rows   dangling %d"
          % ("fts", con.execute("SELECT COUNT(*) FROM fts").fetchone()[0], fts_bad))
    if fts_bad:
        fails.append("fts: %d dangling pointers" % fts_bad)
    print("  total checked %d, dangling %d" % (checked, dangling + fts_bad))

    # ---- leg 4: the seeded question set ------------------------------------
    print("\n[leg 4] the seeded question set - target within the top %d" % top_n)
    hits = 0
    for question, phrase, want in conv.seeded:
        # the bare-pair / list-of-pairs shape is the declaration's, and it is
        # normalised HERE rather than at load - see Conventions.seeded
        targets = want if isinstance(want, list) else [want]
        rows = query(con, phrase, limit=top_n, mech=rec.mech)
        got = None
        for rank, (f, a, t, line, tbl, r) in enumerate(rows, 1):
            if any(f == wf and (wa is None or a == wa) for wf, wa in targets):
                got = rank
                break
        ok = got is not None
        hits += 1 if ok else 0
        tgt = " | ".join("%s · %s" % (wf, wa or "(any anchor)") for wf, wa in targets)
        print("  %-34s %-8s %s" % (question[:34], "rank %d" % got if ok else "MISS", tgt))
        if not ok:
            for rank, (f, a, t, line, tbl, r) in enumerate(rows, 1):
                print("        got %d. %s:%s [%s]" % (rank, f, a, tbl))
            fails.append("seeded question MISS: %s" % question)
    print("  %d / %d" % (hits, len(conv.seeded)))

    # ---- the declaration audit (DIAGNOSTIC) --------------------------------
    print("\n[declaration] corpora declared vs corpora present  (REPORT ONLY)")
    findings = rec.audit_declaration()
    if findings:
        for kind, field, rel in findings[:40]:
            print("  %-24s %-32s %s" % (kind, field, rel))
        if len(findings) > 40:
            print("  ... and %d more" % (len(findings) - 40))
    else:
        print("  every declared corpus is present and every present corpus is "
              "declared or under a declared root")
    print("  %d finding(s)" % len(findings))

    # ---- the vocabulary report (DIAGNOSTIC) --------------------------------
    print("")
    print(rec.vocab.render())
    print("  %s" % rec.mech.calibration_note())

    # CLOSE THE HANDLE. Harmless in a CLI - the process ends a millisecond later
    # - but a long-lived server calls verify and then build in one interpreter,
    # and build starts with os.remove(db_path). On Windows a removal fails while
    # any handle is open.
    con.close()

    print("\n" + "=" * 78)
    print("determinism leg that held: %s" % det_leg)
    if fails:
        print("VERIFY FAILED - %d" % len(fails))
        for f in fails:
            print("  X %s" % f)
        return EXIT_REFUSED
    print("VERIFY PASSED - all four legs")
    return EXIT_OK


def survivable_stdout():
    """Make an unencodable character degrade instead of killing the verifier.

    The loud half of what this tool prints is the RECORD, not its own prose, and
    a record carries characters cp1252 cannot encode. Folding the DATA to ASCII
    is the wrong fix - this tool quotes the record. So the console's encoding is
    kept and only the errors handler is relaxed: a verifier whose FAILURE report
    cannot print is a check that cannot fail.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass
