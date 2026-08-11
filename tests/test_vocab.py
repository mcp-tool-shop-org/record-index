"""vocab.py - the counters that say what a vocabulary did NOT recognise.

THE LAW THIS FILE EXISTS FOR: a missing file raises; a non-matching vocabulary
returns nothing and says nothing. An empty table and a table that silently
discarded six artifacts are indistinguishable at the call site, and only one of
them is correct.

AND THE COUNTER HAS TO BE ABLE TO MOVE. Ask what each metric reads when the arm
does nothing and when it works perfectly; if those are the same number it is not
measuring the arm. Every check below that asserts a non-zero count has a partner
asserting the zero, on the same code path.
"""
import pytest

from record_index.vocab import (PROBE_ANNOUNCED, PROBE_ARTIFACT,
                                PROBE_PHENOMENON, PROBE_RULING_HEADER,
                                PROBE_VERDICT, Vocabulary, VocabReport)


# ---------------------------------------------------------------------------
# the population is what makes the number mean something
# ---------------------------------------------------------------------------

def test_with_no_probe_everything_is_in_the_population():
    v = Vocabulary("open")
    assert v.in_population("anything at all")


def test_a_probe_bounds_the_population():
    v = Vocabulary("verdicts", PROBE_VERDICT)
    assert v.in_population("the pair IS ACCEPTED")
    assert not v.in_population("an ordinary sentence about a BASELINE")


def test_the_announcing_probe_excludes_capitalised_prose():
    """MEASURED. The first draft was `\\b[A-Z]{4,}\\b` and its first run against
    a real record reported 824 unrecognised verdicts - ADJUDICATED, BASELINE,
    OWNER, PASS, SEAM, WHITE - which are capitalised words and not verdicts. A
    counter that cries wolf 824 times is one every reader learns to skip."""
    v = Vocabulary("verdicts", PROBE_ANNOUNCED)
    for prose in ("the BASELINE was measured", "the OWNER is named",
                  "a WHITE background", "SEAM handling"):
        assert not v.in_population(prose), prose


def test_the_announcing_probe_requires_a_past_participle():
    """Narrowed a second time on a stated morphological rule rather than by
    tuning toward a nicer number: a verdict is something DONE to a thing, so it
    is announced as a participle."""
    v = Vocabulary("verdicts", PROBE_ANNOUNCED)
    assert v.in_population("the pair is ACCEPTED")
    assert v.in_population("the arm was RATIFIED")
    for not_a_verdict in ("the answer is NOT", "the state is NOW",
                          "the count is NONE", "the card is WHITE"):
        assert not v.in_population(not_a_verdict), not_a_verdict


def test_the_participle_rule_has_a_stated_blind_spot():
    """A declared verdict that is not a participle is OUTSIDE the population, so
    its holdings are neither hit nor miss. That is a known blind spot of the
    COUNTER and not of the parser - `WITHDRAWN` and `UPHELD` still classify
    exactly as before, and both fixture repos declare one."""
    v = Vocabulary("verdicts", PROBE_ANNOUNCED)
    assert not v.in_population("the alias is WITHDRAWN")
    assert not v.in_population("the first route is UPHELD")


def test_phenomena_and_verdicts_share_the_announcing_form():
    assert PROBE_PHENOMENON == PROBE_ANNOUNCED
    assert PROBE_VERDICT == PROBE_ANNOUNCED


def test_the_ruling_header_probe_is_a_numbered_heading():
    v = Vocabulary("ruling headers", PROBE_RULING_HEADER)
    assert v.in_population("## Ruling 4 - a holding")
    assert v.in_population("## 3. What this file is not")
    assert not v.in_population("## What beta does differently")
    assert not v.in_population("a paragraph mentioning Ruling 4")


def test_the_artifact_probe_is_a_token_with_an_extension():
    v = Vocabulary("artifact kinds", PROBE_ARTIFACT)
    assert v.in_population("outputs/a/b.mp4")
    assert not v.in_population("outputs/a/b")


# ---------------------------------------------------------------------------
# hit, miss, and the arm that can move
# ---------------------------------------------------------------------------

def test_a_complete_vocabulary_reads_zero_and_an_incomplete_one_does_not():
    """THE PAIR THAT MAKES THE COUNTER A MEASUREMENT. Same code path, two
    corpora: one whose extensions are all mapped, one with a gap."""
    complete = Vocabulary("artifact kinds", PROBE_ARTIFACT)
    for _ in range(6):
        complete.hit()
    assert complete.unrecognised == 0
    assert "not recognised" not in complete.line()

    incomplete = Vocabulary("artifact kinds", PROBE_ARTIFACT)
    for _ in range(4):
        incomplete.hit()
    incomplete.miss(".mp4", "docs/a.md:3")
    incomplete.miss(".mkv", "docs/a.md:9")
    assert incomplete.unrecognised == 2
    assert ".mp4" in incomplete.line() and ".mkv" in incomplete.line()


def test_total_is_the_sum_of_both_halves():
    v = Vocabulary("v")
    v.hit()
    v.hit()
    v.miss("x")
    assert (v.recognised, v.unrecognised, v.total) == (2, 1, 3)


def test_a_repeated_token_is_named_once_and_counted_every_time():
    v = Vocabulary("v")
    for _ in range(5):
        v.miss(".mp4", "somewhere")
    assert v.unrecognised == 5
    assert v.samples == [(".mp4", "somewhere")]
    assert "(+4 more occurrence(s))" in v.line()


def test_the_named_list_is_capped_and_says_that_it_was_capped():
    """DISTINCT tokens are capped for legibility; the COUNT is always exact. A
    truncated list that did not say it was truncated would be the same silent
    drop one layer up."""
    v = Vocabulary("v", samples=3)
    for i in range(10):
        v.miss(".x%d" % i, "somewhere")
    assert v.unrecognised == 10
    assert len(v.samples) == 3
    assert "(+7 more occurrence(s))" in v.line()


def test_the_first_site_of_a_token_is_the_one_kept():
    v = Vocabulary("v")
    v.miss(".mp4", "first.md:1")
    v.miss(".mp4", "second.md:9")
    assert v.samples == [(".mp4", "first.md:1")]


# ---------------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------------

def test_a_report_is_built_fresh_and_hands_back_the_same_vocabulary_by_name():
    r = VocabReport()
    a = r.get("verdicts", PROBE_VERDICT)
    b = r.get("verdicts")
    assert a is b


def test_a_report_iterates_in_sorted_name_order():
    r = VocabReport()
    r.get("zeta")
    r.get("alpha")
    r.get("mid")
    assert [v.name for v in r] == ["alpha", "mid", "zeta"]


def test_an_unexercised_report_says_so_rather_than_printing_nothing():
    out = VocabReport().render()
    assert "(no vocabulary was exercised by this build)" in out
    assert "total unrecognised inputs: 0" in out


def test_the_report_says_report_only_on_its_own_face():
    """REPORT, NOT GATE. Which unrecognised inputs matter is a judgement about a
    record, not a property of one, and the section says so where it prints."""
    r = VocabReport()
    r.get("verdicts").miss("BANKED")
    out = r.render()
    assert "REPORT ONLY" in out
    assert "never fails the run" in out
    assert "total unrecognised inputs: 1" in out


def test_total_unrecognised_sums_across_vocabularies():
    r = VocabReport()
    r.get("a").miss("x")
    r.get("b").miss("y")
    r.get("b").miss("z")
    assert r.total_unrecognised == 3


@pytest.mark.parametrize("probe", [PROBE_ANNOUNCED, PROBE_ARTIFACT,
                                   PROBE_RULING_HEADER])
def test_no_probe_matches_the_empty_string(probe):
    """A probe that fired on nothing would put every blank line in some
    vocabulary's population."""
    assert not Vocabulary("v", probe).in_population("")
