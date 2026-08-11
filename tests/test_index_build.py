"""index.py build - the schema, the rows, and the FTS surface.

THE COUNTS ARE HAND-DERIVED from the fixture text (see test_parse.py, where each
corpus is enumerated row by row). What this file adds is what the DATABASE does
with them: the primary keys that make an identity collision impossible, the two
title surfaces that are deliberately not one, and the fact that a build is a
fresh database every time rather than an incremental update.
"""
import os
import sqlite3

import pytest

from record_index import index as I


TABLES = ("rulings", "laws", "experiments", "handoffs", "artifacts",
          "phenomena", "decisions")


# ---------------------------------------------------------------------------
# what a build returns and what it writes
# ---------------------------------------------------------------------------

def test_alphas_build_returns_the_hand_derived_counts(alpha, tmp_path):
    counts = alpha.build(str(tmp_path / "a.db"), quiet=True)
    assert counts == {"rulings": 11, "laws": 8, "experiments": 3, "handoffs": 2,
                      "artifacts": 4, "phenomena": 1, "decisions": 4,
                      "prose_sections": 16, "fts": 49}


def test_betas_build_returns_its_own_counts_which_are_not_alphas(beta, tmp_path):
    counts = beta.build(str(tmp_path / "b.db"), quiet=True)
    assert counts == {"rulings": 4, "laws": 6, "experiments": 2, "handoffs": 0,
                      "artifacts": 3, "phenomena": 0, "decisions": 0,
                      "prose_sections": 3, "fts": 18}


def test_the_declared_empty_corpora_are_empty_tables_and_not_missing_ones(beta_db):
    """`beta has no profiles` is a STATEMENT. It produces a table with no rows,
    which a caller can query, rather than an absent table or a raise."""
    con = sqlite3.connect(beta_db)
    for t in TABLES:
        con.execute("SELECT COUNT(*) FROM %s" % t)
    assert con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM phenomena").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0] == 0
    con.close()


def test_the_counts_returned_match_the_rows_written(alpha, tmp_path):
    """A count returned from a list length while a different list was inserted
    would pass every other check in this file."""
    db = str(tmp_path / "a.db")
    counts = alpha.build(db, quiet=True)
    con = sqlite3.connect(db)
    for t in TABLES:
        assert con.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0] == counts[t]
    assert con.execute("SELECT COUNT(*) FROM fts").fetchone()[0] == counts["fts"]
    con.close()


def test_the_fts_row_count_is_every_structured_row_plus_the_prose(alpha_db):
    con = sqlite3.connect(alpha_db)
    per = dict(con.execute("SELECT tbl, COUNT(*) FROM fts GROUP BY tbl"))
    con.close()
    assert per == {"rulings": 11, "laws": 8, "experiments": 3, "handoffs": 2,
                   "artifacts": 4, "phenomena": 1, "decisions": 4, "prose": 16}


# ---------------------------------------------------------------------------
# the schema
# ---------------------------------------------------------------------------

def test_the_rulings_primary_key_is_arc_number_kind(alpha_db):
    """The key that makes two ruling series numbering from one able to coexist,
    and that raises rather than merging when they cannot."""
    con = sqlite3.connect(alpha_db)
    pk = [r[1] for r in con.execute("PRAGMA table_info(rulings)") if r[5]]
    con.close()
    assert pk == ["arc", "number", "kind"]


def test_experiment_is_a_column_and_not_part_of_any_key(alpha_db):
    con = sqlite3.connect(alpha_db)
    cols = {r[1]: r[5] for r in con.execute("PRAGMA table_info(rulings)")}
    con.close()
    assert "experiment" in cols
    assert cols["experiment"] == 0


def test_every_row_carries_a_file_an_anchor_a_locator_and_a_line(alpha_db):
    con = sqlite3.connect(alpha_db)
    for t in TABLES:
        cols = {r[1] for r in con.execute("PRAGMA table_info(%s)" % t)}
        assert {"file", "anchor", "locator", "line"} <= cols, t
        bad = con.execute(
            "SELECT COUNT(*) FROM %s WHERE file IS NULL OR anchor IS NULL "
            "OR locator IS NULL OR line IS NULL" % t).fetchone()[0]
        assert bad == 0, "%s has %d rows with a null pointer field" % (t, bad)
    con.close()


def test_the_search_title_and_the_displayed_title_are_separate_surfaces(alpha_db):
    """Optimising one degrades the other: a search title packed with arc and
    verdict tokens reads as noise. They must not be the same string on a
    rulings row."""
    con = sqlite3.connect(alpha_db)
    row = con.execute("SELECT title, disp FROM fts WHERE tbl='rulings' "
                      "AND anchor='Ruling 1a'").fetchone()
    con.close()
    assert row[0] != row[1]
    assert "E01" in row[0], "the search title does not carry the arc"
    assert row[1] == "the depth pass is RATIFIED"


def test_the_fts_table_uses_the_declared_tokenizer(alpha_db):
    con = sqlite3.connect(alpha_db)
    sql = con.execute("SELECT sql FROM sqlite_master WHERE name='fts'").fetchone()[0]
    con.close()
    assert "unicode61" in sql and "remove_diacritics 2" in sql


def test_only_the_two_title_columns_are_indexed(alpha_db):
    """`tbl`, `key`, `file`, `anchor`, `locator`, `line` and `disp` are
    UNINDEXED: they are carried so a hit can be resolved to a place in a file,
    not so a query can match on them."""
    con = sqlite3.connect(alpha_db)
    sql = con.execute("SELECT sql FROM sqlite_master WHERE name='fts'").fetchone()[0]
    con.close()
    for col in ("tbl", "key", "file", "anchor", "locator", "line", "disp"):
        assert "%s UNINDEXED" % col in sql


# ---------------------------------------------------------------------------
# a build is a fresh database
# ---------------------------------------------------------------------------

def test_a_build_creates_its_own_output_directory(alpha, tmp_path):
    """Scripts create their own output directories - a law paid for twice."""
    db = str(tmp_path / "nested" / "deeper" / "a.db")
    alpha.build(db, quiet=True)
    assert os.path.exists(db)


def test_a_build_replaces_the_previous_database_rather_than_adding_to_it(
        alpha, tmp_path):
    """Fresh DB each build; never an incremental update. A row left over from a
    previous corpus is a row no verify leg would ever look for."""
    db = str(tmp_path / "a.db")
    alpha.build(db, quiet=True)
    con = sqlite3.connect(db)
    con.execute("INSERT INTO laws VALUES ('a leftover row','law',NULL,NULL,"
                "'x.md','x','x',1)")
    con.commit()
    assert con.execute("SELECT COUNT(*) FROM laws").fetchone()[0] == 9
    con.close()

    alpha.build(db, quiet=True)
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM laws").fetchone()[0] == 8
    assert con.execute("SELECT COUNT(*) FROM laws WHERE statement="
                       "'a leftover row'").fetchone()[0] == 0
    con.close()


def test_a_quiet_build_prints_nothing_and_a_loud_one_prints_the_counts(
        alpha, tmp_path, capsys):
    alpha.build(str(tmp_path / "q.db"), quiet=True)
    assert capsys.readouterr().out == ""
    alpha.build(str(tmp_path / "l.db"), quiet=False)
    out = capsys.readouterr().out
    assert "[build]" in out and "rulings" in out and "11" in out


# ---------------------------------------------------------------------------
# the sequence helpers
# ---------------------------------------------------------------------------

def test_sequence_numbers_reads_plain_and_amendment_numbering(alpha_db):
    con = sqlite3.connect(alpha_db)
    assert I._sequence_numbers(con, "E01", "ruling") == [1, 2]
    assert I._sequence_numbers(con, "E01", "amendment") == [1]
    con.close()


def test_sequence_numbers_ignores_a_lettered_number(alpha_db):
    """`1a` is a sub-ruling's number and is not a point in the parent's
    sequence; counting it would close a gap that is really there."""
    con = sqlite3.connect(alpha_db)
    assert I._sequence_numbers(con, "E01", "sub-ruling") == []
    con.close()


def test_sequence_gaps_finds_a_hole_and_is_silent_on_a_complete_run(alpha_db):
    con = sqlite3.connect(alpha_db)
    assert I._sequence_gaps(con, "E01", "ruling", 1, 2) == []
    assert I._sequence_gaps(con, "E01", "ruling", 1, 5) == [3, 4, 5]
    con.close()


# ---------------------------------------------------------------------------
# survivable stdout
# ---------------------------------------------------------------------------

def test_survivable_stdout_is_safe_to_call_on_a_stream_that_cannot_reconfigure(
        monkeypatch):
    """A verifier whose FAILURE report cannot print is a check that cannot fail,
    so this must degrade rather than raise - including on a captured stream that
    has no `reconfigure` at all."""
    class Dumb(object):
        pass

    monkeypatch.setattr("sys.stdout", Dumb())
    monkeypatch.setattr("sys.stderr", Dumb())
    I.survivable_stdout()


@pytest.mark.parametrize("name,value", [("EXIT_OK", 0), ("EXIT_USER", 1),
                                        ("EXIT_RUNTIME", 2), ("EXIT_PARTIAL", 3),
                                        ("EXIT_REFUSED", 4)])
def test_the_exit_codes_are_the_declared_contract(name, value):
    assert getattr(I, name) == value


def test_no_two_exit_codes_collide():
    """REFUSED must be a code no other outcome class returns, or a caller cannot
    tell `fix your command` from `do not trust this index`."""
    codes = [I.EXIT_OK, I.EXIT_USER, I.EXIT_RUNTIME, I.EXIT_PARTIAL,
             I.EXIT_REFUSED]
    assert len(set(codes)) == len(codes)
