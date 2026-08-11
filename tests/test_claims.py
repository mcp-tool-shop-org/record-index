"""claims.py - the stale-claim sweep. REPORT-ONLY BY RULING, never a gate.

The diagnostic-versus-gate law is the grounds: this sweep swings on phrasing and
on document class, and neither may decide an exit code. It exits 0 whatever it
finds, and the check that it does so is the first one here.

WHAT MAKES A VERDICT is the pair (does the number match, what class of document
said it). alpha's corpus carries one site of every outcome - a stale one, an
as-of-writing one, an ok one, an ambiguous one, an unparseable one, and one the
declaration excludes - so each branch is reached by a real document rather than
by a constructed string.
"""
import io
import json
import os

import pytest

import record_index
from record_index import claims as C
from record_index.conventions import Conventions
from record_index.parse import Record


def _rows(out):
    """The verdict column of every claim row the sweep printed."""
    got = []
    for ln in out.split("\n"):
        parts = ln.split()
        if parts and parts[0] in ("STALE", "AMBIGUOUS", "ok", "as-of-writing"):
            got.append((parts[0], ln.rsplit(" ", 1)[-1]))
    return got


# ---------------------------------------------------------------------------
# it never gates
# ---------------------------------------------------------------------------

def test_the_sweep_exits_zero_with_stale_rows_on_the_record(alpha, alpha_db,
                                                            capsys):
    """alpha carries two STALE rows on purpose. The verb still exits 0, because
    stale sites are an advisor's to rule and never a tool's to fix."""
    assert alpha.claims(alpha_db) == 0
    out = capsys.readouterr().out
    assert "REPORT-ONLY; always exits 0" in out
    assert "STALE (current-state documents disagreeing with the record): 2" in out


def test_the_sweep_exits_zero_on_a_record_with_nothing_to_say(beta, beta_db,
                                                              capsys):
    assert beta.claims(beta_db) == 0
    assert "always exits 0" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# the measurements come from the index, not from a second derivation
# ---------------------------------------------------------------------------

def test_the_sweep_reads_the_index_rather_than_re_deriving_the_record(alpha_db):
    """A second derivation here would be a second authority. The index already
    did that derivation under the ratified verify legs."""
    import sqlite3
    con = sqlite3.connect(alpha_db)
    m = C.measurements(con)
    con.close()
    assert m[("E01", "ruling")] == {"count": 2, "max": 2}
    assert m[("E02-offsurface", "ruling")] == {"count": 2, "max": 2}
    assert m[("E01", "handoff")] == {"count": 2, "max": 2}
    assert m[("E01", "amendment")] == {"count": 1, "max": 1}
    assert m[("*", "experiment")] == {"count": 3, "max": 3}


# ---------------------------------------------------------------------------
# the four verdicts
# ---------------------------------------------------------------------------

def test_a_current_state_document_disagreeing_with_the_record_is_stale(
        alpha, alpha_db, capsys):
    alpha.claims(alpha_db)
    out = capsys.readouterr().out
    assert "OVERVIEW.md:20  claims count 3, record has count 2" in out


def test_a_current_state_directory_reaches_stale_through_the_other_branch(
        alpha, alpha_db, capsys):
    """Two ways into the same class - the declared file list and the declared
    directory list - and both must work, or a repo that organises its live
    documents into a folder gets a sweep that never fires."""
    alpha.claims(alpha_db)
    out = capsys.readouterr().out
    assert "docs/handbook/index.md:8  claims count 5, record has count 2" in out


def test_a_historical_document_disagreeing_is_as_of_writing_and_not_stale(
        alpha, alpha_db, capsys):
    """A kickoff, spec, report or released changelog entry states its counts as
    of writing. Calling that staleness would flag the record's own history."""
    alpha.claims(alpha_db)
    out = capsys.readouterr().out
    assert "as-of-writing" in out
    assert "CHANGELOG.md:10" in out
    assert "CHANGELOG.md:10  claims" not in out.split("STALE (")[1]


def test_a_matching_count_in_a_current_state_document_is_ok(alpha, alpha_db,
                                                            capsys):
    alpha.claims(alpha_db)
    assert ("ok", "CHANGELOG.md:5") in _rows(capsys.readouterr().out)


def test_a_modifier_makes_an_assertion_ambiguous_rather_than_resolved(
        alpha, alpha_db, capsys):
    """`2 rulings so far` is a true count wearing a modifier the sweep cannot
    resolve. Reporting it as ok would be a guess and reporting it as stale would
    be a wrong one."""
    alpha.claims(alpha_db)
    out = capsys.readouterr().out
    assert "AMBIGUOUS (a modifier makes the assertion unresolvable): 1" in out
    assert "so far" in out


def test_a_count_claim_no_family_parses_is_reported_not_guessed_at(
        alpha, alpha_db, capsys):
    alpha.claims(alpha_db)
    out = capsys.readouterr().out
    assert "UNPARSEABLE (count-claim-shaped, no family): 1" in out
    assert '"3 experiments"' in out


# ---------------------------------------------------------------------------
# the document classes
# ---------------------------------------------------------------------------

def test_the_changelog_splits_at_its_first_release(alpha):
    """Above the first released heading is the present tense; inside a released
    entry is history."""
    rec = alpha.record()
    assert C.classify_document(rec, "CHANGELOG.md", 5)[0] == "current-state"
    assert C.classify_document(rec, "CHANGELOG.md", 10)[0] == "historical"
    assert "above the first release" in C.classify_document(rec, "CHANGELOG.md", 5)[1]


def test_a_bannered_document_splits_at_its_banner(alpha, alpha_conv,
                                                  copy_fixture):
    root = copy_fixture("alpha")
    p = os.path.join(root, "docs", "banner.md")
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# live above\n\nstill current\n\n"
                 "## SUPERSEDED — everything below is history\n\nold text\n")
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["sweep"]["bannered"] = "docs/banner.md"
    rec = Record(root, Conventions(doc))
    assert C.classify_document(rec, "docs/banner.md", 3)[0] == "current-state"
    assert C.classify_document(rec, "docs/banner.md", 9)[0] == "historical"


def test_a_bannered_document_with_no_banner_is_all_current_state(
        alpha, alpha_conv, copy_fixture):
    root = copy_fixture("alpha")
    p = os.path.join(root, "docs", "banner.md")
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# no banner here\n\nall of it is live.\n")
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["sweep"]["bannered"] = "docs/banner.md"
    rec = Record(root, Conventions(doc))
    cls, why = C.classify_document(rec, "docs/banner.md", 9)
    assert cls == "current-state"
    assert "no banner found" in why


def test_a_document_on_neither_list_is_reported_and_not_assigned(alpha):
    """`unclassified` is a real answer. Guessing a class would decide a verdict
    on the strength of a guess."""
    cls, why = C.classify_document(alpha.record(), "docs/nowhere.md", 1)
    assert cls == "unclassified"
    assert "reported, not assigned" in why


def test_the_two_repos_classify_the_same_path_differently(alpha, beta):
    """The class lists are declared. A path that is history in one repo is not
    even known to the other."""
    assert C.classify_document(alpha.record(), "CLAUDE.md", 1)[0] == "current-state"
    assert C.classify_document(beta.record(), "CLAUDE.md", 1)[0] == "unclassified"
    assert C.classify_document(beta.record(), "LAWS.md", 1)[0] == "current-state"


# ---------------------------------------------------------------------------
# the self-reference exclusion
# ---------------------------------------------------------------------------

def test_a_document_the_declaration_excludes_contributes_nothing(alpha, alpha_db,
                                                                 capsys):
    """LIFTED from a function body: this was an inline `startswith("E15-")`, one
    repo's own exclusion with no constant name. Documents that QUOTE these
    counts as data would otherwise flag the sweep's own subject matter."""
    alpha.claims(alpha_db)
    assert "E02-report.md" not in capsys.readouterr().out


def test_removing_the_exclusion_makes_the_same_line_appear(alpha, alpha_conv,
                                                           alpha_db, capsys):
    """CAN-FAIL LEG. Without it, the silence above would pass equally well on a
    sweep that never read the file for any reason."""
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["sweep"]["self_reference_exclude"] = []
    rec = Record(alpha.root, Conventions(doc))
    C.claims(rec, alpha_db)
    out = capsys.readouterr().out
    assert "E02-report.md" in out
    assert "as-of-writing" in out


# ---------------------------------------------------------------------------
# the phrasing families
# ---------------------------------------------------------------------------

def test_the_families_are_the_repos_own_and_absent_ones_are_named(alpha,
                                                                  alpha_db,
                                                                  capsys):
    """A family list copied from another repo finds zero sites and reports
    nothing wrong, so the families with no site are named out loud."""
    alpha.claims(alpha_db)
    out = capsys.readouterr().out
    assert "rulings cardinal      5 site(s)" in out
    assert "families with no site on the current record: rulings range, " \
           "handoffs cardinal, experiment span" in out


def test_betas_own_phrasing_family_finds_betas_own_sites(beta, beta_db, capsys):
    """beta's record says `decisions` where alpha's says `rulings`. The family
    is declared, so beta finds its two sites where alpha's families would find
    none."""
    beta.claims(beta_db)
    out = capsys.readouterr().out
    assert "decisions cardinal    2 site(s)" in out


@pytest.mark.xfail(strict=True, reason=(
    "FINDING. `claims.ARC_RE` is the module constant `\\bE(\\d\\d)\\b` — the "
    "arc form of the repo this package was extracted from, hard-coded. Every "
    "other arc-shaped value in the package is declared: `discovery.ruling_arc`, "
    "`discovery.experiment_prefix`, `sweep.claim_families`, "
    "`laws.paid_for_by`. This one is not, so a repo whose arcs are not "
    "`E<dd>` cannot attribute any count claim to any arc. Measured on beta, "
    "whose arcs are A01 and A02: its two declared-family sites both land in "
    "the unparseable list with `no arc attributable on this line`, its STALE "
    "count is 0, and the claim that live/status.md is wrong by five is never "
    "made. `measurements()` carries the same assumption in "
    "`CAST(substr(id,2) AS INTEGER)`, which reads an experiment id as one "
    "prefix character plus digits."))
def test_a_repo_whose_arcs_are_not_e_numbered_can_still_attribute_a_claim(
        beta, beta_db, capsys):
    beta.claims(beta_db)
    out = capsys.readouterr().out
    assert "STALE (current-state documents disagreeing with the record): 1" in out
    assert "live/status.md:8  claims count 7, record has count 2" in out


def test_the_arc_pattern_is_the_e_form_and_beta_pays_for_it(beta, beta_db,
                                                            capsys):
    """THE SAME MEASUREMENT, pinned as behaviour so the finding above carries a
    number. Both of beta's declared-family sites are reported as unparseable
    for want of an arc, and the sweep still exits 0."""
    assert beta.claims(beta_db) == 0
    out = capsys.readouterr().out
    assert "UNPARSEABLE (count-claim-shaped, no family): 2" in out
    assert 'OVERVIEW.md:8  "2 decisions"  - no arc attributable' in out
    assert 'live/status.md:8  "7 decisions"  - no arc attributable' in out
    assert "STALE (current-state documents disagreeing with the record): 0" in out


def test_a_range_that_does_not_start_at_one_is_not_a_count_claim():
    """`Rulings 1-30` asserts thirty exist; `Rulings 21-23` names three of them
    and asserts nothing about the total. An earlier pattern did not distinguish
    them and reported 35 references as unparseable - noise that would have
    buried the rows that matter."""
    assert C.CLAIM_SHAPED.search("Rulings 1-30")
    assert not C.CLAIM_SHAPED.search("Rulings 21-23")


def test_claim_shaped_is_case_insensitive():
    assert C.CLAIM_SHAPED.search("7 RULINGS")
    assert C.CLAIM_SHAPED.search("7 rulings")


def test_the_arc_pattern_needs_exactly_two_digits():
    assert C.ARC_RE.findall("E01 and E12") == ["01", "12"]
    assert C.ARC_RE.findall("E1 and E123") == []


def test_a_claim_on_a_line_naming_no_arc_is_unparseable(alpha, alpha_conv,
                                                        alpha_db, copy_fixture,
                                                        capsys):
    """A count with no arc attributable is reported as unparseable rather than
    attributed to whichever arc happened to be nearby."""
    root = copy_fixture("alpha")
    with io.open(os.path.join(root, "OVERVIEW.md"), "a", encoding="utf-8",
                 newline="\n") as fh:
        fh.write("\nSomewhere the record carries 12 rulings, with no arc named.\n")
    C.claims(Record(root, alpha_conv), alpha_db)
    out = capsys.readouterr().out
    assert "no arc attributable on this line" in out
