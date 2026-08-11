"""index.query - two-stage retrieval, and why it is two stages.

WHY NOT BM25 ALONE: a record repeats its vocabulary across arcs, so a
disjunction ranks a row matching a few common terms alongside one matching every
term. WHY COVERAGE SCALES BM25 RATHER THAN OVERRIDING IT: overriding was tried
and falsified elsewhere - coordination level as primary sort scored 9/14 against
bm25's 12/14, title-coverage-first 11/14, and scaling 13/14.

Every mechanism here is generic. None of it knows about a document, and the
checks below run the same phrases against both fixture corpora to keep it that
way.
"""
import sqlite3

import pytest

from record_index import index as I
from record_index.mechanism import Mechanism


@pytest.fixture
def con_a(alpha_db):
    con = sqlite3.connect(alpha_db)
    yield con
    con.close()


@pytest.fixture
def con_b(beta_db):
    con = sqlite3.connect(beta_db)
    yield con
    con.close()


def keys(rows):
    return [(r[0], r[1]) for r in rows]


# ---------------------------------------------------------------------------
# it finds things
# ---------------------------------------------------------------------------

def test_a_distinctive_phrase_returns_its_own_row_first(con_a):
    rows = I.query(con_a, "between-generation floor portable repeat runs seed")
    assert keys(rows)[0] == ("docs/experiments/E02-ruling.md", "Ruling 2")


def test_the_same_mechanism_works_on_the_second_corpus(con_b):
    rows = I.query(con_b, "the second clip is OVERTURNED")
    assert keys(rows)[0] == ("record/arcs/A02-decision.md", "Ruling 1a")


def test_a_phrase_matching_nothing_returns_nothing(con_a):
    assert I.query(con_a, "zygomorphic tessellation quinquagenarian") == []


def test_the_limit_is_respected(con_a):
    assert len(I.query(con_a, "the record and the ruling", limit=2)) <= 2


def test_a_row_is_returned_once_even_when_both_stages_find_it(con_a):
    rows = I.query(con_a, "the depth pass is RATIFIED", limit=20)
    assert len(keys(rows)) == len(set(keys(rows)))


# ---------------------------------------------------------------------------
# the two stages
# ---------------------------------------------------------------------------

def test_the_exact_phrase_stage_keeps_stopwords_because_a_phrase_is_adjacency(
        con_a):
    """Stage 1 runs over the FULL word run with stopwords KEPT: a phrase is
    adjacency, and dropping `the`/`is` breaks it."""
    exact = I.query(con_a, "the alias question is closed", limit=1)
    assert keys(exact)[0] == ("docs/experiments/E01-ruling.md", "Ruling 1b-CLOSED")


def test_the_phrase_stage_is_a_best_bet_slot_and_not_a_takeover(con_a):
    """Uncapped, a phrase appearing in a pointer document monopolises the page.
    With the cap at one, at most one row can enter from stage 1."""
    tight = Mechanism(PHRASE_SLOTS=1)
    rows = I.query(con_a, "the record is a decision record", limit=8, mech=tight)
    assert len(rows) <= 8


def test_a_single_word_phrase_skips_the_adjacency_stage(con_a):
    """Stage 1 needs more than one word to be a phrase at all; a single term
    must still return its rows through stage 2."""
    rows = I.query(con_a, "RATIFIED")
    assert rows


def test_coverage_scales_the_score_rather_than_replacing_it(con_a):
    """A row matching every term of a query must outrank one matching a single
    common term, WITHOUT discarding bm25's length normalisation - which is what
    an override rather than a scale would do."""
    rows = keys(I.query(con_a, "off-surface margin banked measured phenomenon",
                        limit=8))
    top = rows[0]
    assert top[0] == "docs/experiments/E02-offsurface-ruling.md"
    assert ("docs/experiments/E01-spec.md", "Out of scope") not in rows[:2]


# ---------------------------------------------------------------------------
# it is deterministic
# ---------------------------------------------------------------------------

def test_the_same_query_returns_the_same_order_every_time(con_a):
    """`q` is deterministic by construction: the re-ranking window is fixed
    rather than derived, and ties break on file then line."""
    first = I.query(con_a, "the ruling and the record and the arc", limit=8)
    for _ in range(4):
        assert I.query(con_a, "the ruling and the record and the arc",
                       limit=8) == first


def test_two_builds_of_one_corpus_rank_a_query_identically(alpha, tmp_path):
    a, b = str(tmp_path / "a.db"), str(tmp_path / "b.db")
    alpha.build(a, quiet=True)
    alpha.build(b, quiet=True)
    ca, cb = sqlite3.connect(a), sqlite3.connect(b)
    try:
        for phrase in ("the depth pass normalization ratified manifest",
                       "big binaries stay out of git renders committed",
                       "the arc and the ruling"):
            assert I.query(ca, phrase, limit=8) == I.query(cb, phrase, limit=8)
    finally:
        ca.close()
        cb.close()


# ---------------------------------------------------------------------------
# the mechanism is a parameter
# ---------------------------------------------------------------------------

def test_the_candidate_window_bounds_the_relaxed_stage(con_a):
    """The window is tuning, not a convention, and it is a real parameter: one
    candidate cannot return more rows than one."""
    narrow = Mechanism(CANDIDATES=1, PHRASE_SLOTS=0)
    rows = I.query(con_a, "ruling record arc", limit=8, mech=narrow)
    assert len(rows) <= 1


def test_query_falls_back_to_the_module_default_when_given_no_mechanism(con_a):
    assert I.query(con_a, "the depth pass", limit=3) == \
        I.query(con_a, "the depth pass", limit=3, mech=I.DEFAULT)


# ---------------------------------------------------------------------------
# the binding's own verb
# ---------------------------------------------------------------------------

def test_the_bindings_query_carries_the_bindings_mechanism(alpha, alpha_conv,
                                                           alpha_db):
    import record_index
    con = sqlite3.connect(alpha_db)
    try:
        tight = record_index.Binding(alpha.root, alpha_conv,
                                     Mechanism(CANDIDATES=1, PHRASE_SLOTS=0))
        assert len(tight.query(con, "ruling record arc", limit=8)) <= 1
        assert len(alpha.query(con, "ruling record arc", limit=8)) > 1
    finally:
        con.close()
