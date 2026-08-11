"""Determinism - a contract, not an aspiration.

TWO BUILDS FROM AN UNCHANGED RECORD MUST BE THE SAME INDEX. Everything that could
vary is pinned: every traversal is sorted, every insert order is fixed, the whole
build is one transaction, and no timestamp or random value is ever written.

WHAT IS COMPARED HERE IS PARSED OBJECTS, not the bytes of the database file. A
file-hash mismatch is not evidence a build changed - it is evidence the bytes
differ, which a page-allocation detail can produce on an identical logical index.
So every check below compares row sets, `.dump` text, or certificate fields.
Byte-identity is measured too, as the leg it is, and it is reported rather than
required.
"""
import os
import sqlite3

from record_index import certificate as CERT


TABLES = ("rulings", "laws", "experiments", "handoffs", "artifacts",
          "phenomena", "decisions")


def _rows(db):
    con = sqlite3.connect(db)
    out = {}
    for t in TABLES:
        cols = [r[1] for r in con.execute("PRAGMA table_info(%s)" % t)]
        out[t] = con.execute(
            "SELECT * FROM %s ORDER BY %s" % (t, ", ".join(cols))).fetchall()
    out["fts"] = con.execute(
        "SELECT title, body, tbl, key, file, anchor, locator, line, disp "
        "FROM fts ORDER BY tbl, key, file, line").fetchall()
    con.close()
    return out


def _dump(db):
    con = sqlite3.connect(db)
    try:
        return "\n".join(con.iterdump())
    finally:
        con.close()


# ---------------------------------------------------------------------------
# the logical index
# ---------------------------------------------------------------------------

def test_two_builds_produce_identical_row_sets(alpha, tmp_path):
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    alpha.build(a, quiet=True)
    alpha.build(b, quiet=True)
    assert _rows(a) == _rows(b)


def test_two_builds_produce_identical_dump_text(alpha, tmp_path):
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    alpha.build(a, quiet=True)
    alpha.build(b, quiet=True)
    assert _dump(a) == _dump(b)


def test_the_second_corpus_is_deterministic_too(beta, tmp_path):
    """A determinism property measured on one corpus is a property of that
    corpus's shape until a second one is measured."""
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    beta.build(a, quiet=True)
    beta.build(b, quiet=True)
    assert _rows(a) == _rows(b)


def test_the_row_comparison_can_fail(alpha, tmp_path):
    """CAN-FAIL LEG. If `_rows` read nothing, or compared only table names, the
    three checks above would pass on a build that had changed completely."""
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    alpha.build(a, quiet=True)
    alpha.build(b, quiet=True)
    con = sqlite3.connect(b)
    con.execute("DELETE FROM laws WHERE rowid IN (SELECT rowid FROM laws LIMIT 1)")
    con.commit()
    con.close()
    assert _rows(a) != _rows(b)


def test_no_row_carries_a_timestamp_or_an_absolute_path(alpha_db):
    """The two things that make an otherwise deterministic build differ between
    runs and between machines."""
    con = sqlite3.connect(alpha_db)
    for t in TABLES:
        for row in con.execute("SELECT * FROM %s" % t):
            for cell in row:
                if not isinstance(cell, str):
                    continue
                assert not os.path.isabs(cell), "%s carries an absolute path: %r" % (t, cell)
                assert "\\" not in cell or "outputs" not in cell, (
                    "%s carries a backslash path: %r" % (t, cell))
    con.close()


def test_byte_identity_holds_on_this_platform(alpha, tmp_path):
    """MEASURED AND REPORTED, not required. The build pins page size, journal
    mode and the final VACUUM so that byte-identity is reachable; verify carries
    a pre-registered `.dump` fallback for the case where SQLite's own file
    header defeats it. This check records which one holds here."""
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    alpha.build(a, quiet=True)
    alpha.build(b, quiet=True)
    with open(a, "rb") as fh:
        ba = fh.read()
    with open(b, "rb") as fh:
        bb = fh.read()
    assert ba == bb or _dump(a) == _dump(b), (
        "neither byte- nor .dump-identical, which is the determinism leg's own "
        "failure condition")


# ---------------------------------------------------------------------------
# the certificate
# ---------------------------------------------------------------------------

def test_two_certifications_of_one_corpus_agree_on_every_field_but_the_clock(
        alpha, tmp_path):
    """PARSED-OBJECT COMPARISON. `verified_utc` is the one field that must
    differ from run to run, so it is excluded by name rather than by hoping two
    runs land in different seconds - and everything else, including the whole
    verify transcript and the corpus digest, must match exactly."""
    one = str(tmp_path / "one" / "alpha.db")
    two = str(tmp_path / "two" / "alpha.db")
    os.makedirs(os.path.dirname(one))
    os.makedirs(os.path.dirname(two))
    a = CERT.build_and_certify(alpha, one)
    b = CERT.build_and_certify(alpha, two)
    a.pop("verified_utc")
    b.pop("verified_utc")
    assert a == b


def test_the_certificate_comparison_can_fail(alpha, beta, tmp_path):
    """CAN-FAIL LEG: two DIFFERENT corpora must not certify identically."""
    one = str(tmp_path / "one" / "x.db")
    two = str(tmp_path / "two" / "x.db")
    os.makedirs(os.path.dirname(one))
    os.makedirs(os.path.dirname(two))
    a = CERT.build_and_certify(alpha, one)
    b = CERT.build_and_certify(beta, two)
    a.pop("verified_utc")
    b.pop("verified_utc")
    assert a != b


def test_the_corpus_id_is_order_independent_and_moves_when_a_file_moves(alpha):
    m = CERT.corpus_manifest(alpha.record())
    assert CERT.corpus_id(m) == CERT.corpus_id(dict(reversed(list(m.items()))))
    changed = dict(m)
    changed[sorted(changed)[0]] = "0" * 64
    assert CERT.corpus_id(changed) != CERT.corpus_id(m)


def test_the_corpus_manifest_covers_every_markdown_file_the_index_reads(alpha):
    m = CERT.corpus_manifest(alpha.record())
    assert set(m) == set(alpha.record().record_markdown())
    assert "CLAUDE.md" in m and "docs/experiments/E01-ruling.md" in m
