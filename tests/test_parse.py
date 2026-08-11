"""parse.py - the parsers, each one reading a declaration.

THE ROW COUNTS BELOW ARE HAND-DERIVED FROM THE FIXTURE TEXT, not copied out of a
run. Both corpora are small enough for that to be possible, which is the reason
they are small: a suite that asserted whatever the first run produced would pin
the behaviour and measure none of it.

THIS FILE NEVER WRITES TO A RECORD is the module's own first law, and the checks
that matter most here are the ones where a wrong implementation would still
produce plausible output - a locator that points at nothing, a verdict read out
of a lower-case adjective, a sub-ruling attributed to the ruling it merely
cross-references, a parent that re-indexes its own children's prose.
"""
import io
import json
import os
import shutil
import sqlite3

import pytest

import record_index
from record_index import index as I
from record_index.conventions import Conventions
from record_index.parse import Record


# ---------------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------------

def test_alpha_discovers_three_ruling_documents_and_one_kickoff(alpha):
    rec = alpha.record()
    assert [(a, e, r) for a, e, r in rec.ruling_documents()] == [
        ("E01", "E01", "docs/experiments/E01-ruling.md"),
        ("E02-offsurface", "E02", "docs/experiments/E02-offsurface-ruling.md"),
        ("E02", "E02", "docs/experiments/E02-ruling.md"),
    ]
    assert rec.handoff_documents() == [
        ("E01", "E01", "docs/experiments/E01-executor-kickoff.md")]


def test_arc_is_identity_and_experiment_is_grouping(alpha):
    """Two documents, one experiment, TWO arcs. `arc` is part of the rulings
    primary key so it stays stem-derived; `experiment` is the prefix as a
    non-key column, so `experiment='E02'` is one WHERE clause and costs no row
    its identity."""
    rec = alpha.record()
    docs = {rel: (arc, exp) for arc, exp, rel in rec.ruling_documents()}
    assert docs["docs/experiments/E02-ruling.md"] == ("E02", "E02")
    assert docs["docs/experiments/E02-offsurface-ruling.md"] == ("E02-offsurface", "E02")


def test_beta_discovers_its_own_documents_and_zero_kickoffs(beta):
    """beta's kickoff pattern matches nothing today, which is measured rather
    than assumed: the pattern is declared so a brief, if one is ever written, is
    discovered rather than silently missed."""
    rec = beta.record()
    assert [rel for _, _, rel in rec.ruling_documents()] == [
        "record/arcs/A01-decision.md", "record/arcs/A02-decision.md"]
    assert rec.handoff_documents() == []


def test_a_document_matching_neither_pattern_is_discovered_by_neither(beta):
    rec = beta.record()
    found = [rel for _, _, rel in rec.ruling_documents()]
    assert "record/arcs/A02-report.md" not in found


# ---------------------------------------------------------------------------
# rulings
# ---------------------------------------------------------------------------

def test_alphas_eleven_rulings_are_exactly_these(alpha):
    """The order is the declared sort: arc, then the numeric part, then the
    letter, then the kind - so a parent, its addendum and its amendment sit
    together under one number and the sub-rulings follow in letter order."""
    rows = alpha.record().parse_rulings()
    assert [(r["arc"], r["number"], r["kind"]) for r in rows] == [
        ("E01", "1", "addendum"),
        ("E01", "A1", "amendment"),
        ("E01", "1", "ruling"),
        ("E01", "1a", "sub-ruling"),
        ("E01", "1b", "sub-ruling"),
        ("E01", "1b-CLOSED", "sub-ruling-closure"),
        ("E01", "2", "ruling"),
        ("E02", "1", "ruling"),
        ("E02", "2", "ruling"),
        ("E02-offsurface", "1", "ruling"),
        ("E02-offsurface", "2", "ruling"),
    ]


def test_the_two_e02_documents_do_not_collide(alpha_db):
    """THE COLLISION THIS DESIGN EXISTS TO AVOID, from the other side: keyed on
    the stem the two documents are two arcs and both index, so `E02` and
    `E02-offsurface` each carry rulings 1 and 2."""
    con = sqlite3.connect(alpha_db)
    got = con.execute("SELECT arc, number FROM rulings WHERE kind='ruling' "
                      "AND experiment='E02' ORDER BY arc, number").fetchall()
    con.close()
    assert got == [("E02", "1"), ("E02", "2"),
                   ("E02-offsurface", "1"), ("E02-offsurface", "2")]


def test_the_leading_prefix_rule_really_does_collide_on_this_corpus(
        alpha, alpha_conv, tmp_path):
    """THE CAN-FAIL LEG for the test above, and the measurement the design
    correction was made from. Swap only the arc rule to the leading `E\\d\\d`
    prefix and the same corpus raises IntegrityError on a duplicated primary
    key - so the choice above is load-bearing and not decorative."""
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["discovery"]["ruling_arc"] = {"leading": True}
    conv = Conventions(doc)
    rec = Record(alpha.root, conv)
    with pytest.raises(sqlite3.IntegrityError):
        I.build(rec, str(tmp_path / "collide.db"), quiet=True)


def test_a_sub_rulings_locator_is_findable_in_its_own_file(alpha):
    """LEG 3'S PROPERTY, at the source. `anchor` is the human label a session
    cites; `locator` is the exact string findable in the file, because GitHub
    mints anchors for `#`-headings only and a bold lead is not one."""
    rec = alpha.record()
    cache = {}
    for r in rec.parse_rulings():
        src = cache.setdefault(r["file"], rec.read(r["file"]))
        assert r["locator"] in src, (
            "%s %s: locator %r is not in %s"
            % (r["kind"], r["number"], r["locator"], r["file"]))


def test_the_closure_marker_is_a_different_kind_from_a_sub_ruling(alpha):
    rows = {(r["number"], r["kind"]) for r in alpha.record().parse_rulings()}
    assert ("1b", "sub-ruling") in rows
    assert ("1b-CLOSED", "sub-ruling-closure") in rows


def test_a_sub_ruling_takes_its_parents_date_when_it_carries_none(alpha):
    rows = {(r["arc"], r["number"], r["kind"]): r
            for r in alpha.record().parse_rulings()}
    assert rows[("E01", "1", "ruling")]["date"] == "2026-01-05"
    assert rows[("E01", "1a", "sub-ruling")]["date"] == "2026-01-05"
    # and a header carrying no date falls back to the head of its own body
    assert rows[("E02", "1", "ruling")]["date"] == "2026-02-01"


def test_a_parent_does_not_re_index_its_own_sub_rulings_prose(alpha):
    """Every sub is its own row, so including their text in the parent makes the
    parent compete with its own children and dilutes bm25's length
    normalisation for both."""
    rows = {(r["arc"], r["number"], r["kind"]): r
            for r in alpha.record().parse_rulings()}
    assert "depth pass" not in rows[("E01", "1", "ruling")]["body"]
    assert "depth pass" in rows[("E01", "1a", "sub-ruling")]["body"]


def test_a_lettered_marker_numbered_for_another_ruling_is_a_cross_reference(
        alpha, copy_fixture):
    """A paragraph opening `**2a - ...` inside Ruling 1's block belongs to
    Ruling 2 and is a cross-reference, not this ruling's own sub. It is skipped
    and RECORDED as skipped rather than silently attached to the wrong parent."""
    root = copy_fixture("alpha")
    p = os.path.join(root, "docs", "experiments", "E01-ruling.md")
    with io.open(p, encoding="utf-8") as fh:
        src = fh.read()
    src = src.replace(
        "**1b — the alias is WITHDRAWN**",
        "**2a — a cross-reference to the other ruling**")
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)

    rec = Record(root, alpha.conv)
    rows = {(r["arc"], r["number"]) for r in rec.parse_rulings()}
    assert ("E01", "2a") not in rows
    assert rec.skipped_crossrefs, "the skip was not recorded anywhere"
    assert rec.skipped_crossrefs[0][0] == "docs/experiments/E01-ruling.md"


def test_beta_merges_two_declared_header_forms_in_one_document(beta):
    """A shared tool that hard-codes one ruling-header form reads the other
    document as zero rows and says nothing about it. Both forms live in
    A01-decision.md, and both must index, in line order."""
    rows = [r for r in beta.record().parse_rulings() if r["arc"] == "A01"]
    assert [(r["number"], r["line"]) for r in rows] == [("1", 6), ("2", 11)]
    assert rows[0]["locator"].startswith("## 1. RULING")
    assert rows[1]["locator"].startswith("## Decision 2")


def test_beta_counts_the_numbered_heading_no_declared_form_reads(beta):
    """THE COUNTER THAT WOULD HAVE CAUGHT A SECOND RECORD'S HEADER FORM on its
    first build instead of leaving three documents silently at zero rows."""
    rec = beta.record()
    rec.parse_rulings()
    v = rec.vocab.get("ruling headers")
    assert v.recognised == 1
    assert v.unrecognised == 1
    assert v.samples[0][0].startswith("## 3.")


def test_alpha_has_no_unrecognised_ruling_headers(alpha):
    """THE ZERO SIDE of the check above, on the corpus whose declaration is
    complete. Two different numbers on the same code path is what makes it a
    measurement."""
    rec = alpha.record()
    rec.parse_rulings()
    assert rec.vocab.get("ruling headers").unrecognised == 0


# ---------------------------------------------------------------------------
# classify - the capitals ARE the convention
# ---------------------------------------------------------------------------

def test_capitals_carry_the_verdict_and_lower_case_does_not(alpha):
    """MEASURED THE HARD WAY ELSEWHERE: an earlier version upper-cased the
    holding first and so marked three rulings ACCEPTED that accept nothing. A
    verdict is what a ruling DOES and the record shouts it; the same word in
    lower case is an adjective describing an artifact."""
    rec = alpha.record()
    assert rec.classify("the second bridge is ACCEPTED")[0] == "ACCEPTED"
    assert rec.classify("the alias question is closed")[0] is None
    assert rec.classify("an accepted convention")[0] is None


def test_a_verdict_needs_word_boundaries(alpha):
    rec = alpha.record()
    assert rec.classify("the run is UNACCEPTED here")[0] is None


def test_authority_is_the_declared_word_and_defaults_to_the_declared_default(
        alpha, beta):
    a, b = alpha.record(), beta.record()
    assert a.classify("the Director's eye RATIFIED it") == ("RATIFIED", "Director")
    assert a.classify("the advisor ruled it ACCEPTED") == ("ACCEPTED", "advisor")
    # beta's authority word and default are different words entirely
    assert b.classify("the Chief looked at it")[1] == "Chief"
    assert b.classify("nobody senior looked at it")[1] == "deputy"
    assert a.classify("the Chief looked at it")[1] == "advisor"


def test_the_verdict_counter_names_the_shouted_verbs_nobody_declared(alpha):
    """The population is a holding that ANNOUNCES. A shouted verb the
    vocabulary does not claim is a real miss, and it is NAMED so the reader can
    decide whether the vocabulary is short or the sentence is not a verdict."""
    rec = alpha.record()
    for r in rec.parse_rulings():
        rec.classify(r["holding"])
    v = rec.vocab.get("verdicts")
    assert v.recognised == 4
    assert [t for t, _ in v.samples] == ["BANKED", "CORRECTED", "MEASURED"]


# ---------------------------------------------------------------------------
# supersessions
# ---------------------------------------------------------------------------

def test_an_explicit_correction_links_both_directions(alpha):
    rec = alpha.record()
    rows = rec.parse_rulings()
    rec.link_supersessions(rows)
    by = {(r["arc"], r["number"]): r for r in rows}
    assert by[("E01", "A1")]["supersedes"] == "1"
    assert by[("E01", "1")]["superseded_by"] == "A1"


def test_a_ruling_never_supersedes_itself(alpha):
    rec = alpha.record()
    rows = rec.parse_rulings()
    rec.link_supersessions(rows)
    for r in rows:
        assert r["number"] not in (r["supersedes"] or "").split(",")


def test_a_correction_naming_a_number_in_another_arc_is_not_linked(alpha):
    """`by_key` is (arc, number), so a correction can only reach its own arc.
    Cross-arc guessing is exactly the mis-attribution the conservative patterns
    exist to avoid."""
    rec = alpha.record()
    rows = rec.parse_rulings()
    rec.link_supersessions(rows)
    by = {(r["arc"], r["number"]): r for r in rows}
    assert by[("E02", "1")]["superseded_by"] is None


# ---------------------------------------------------------------------------
# laws
# ---------------------------------------------------------------------------

def test_alphas_law_book_yields_all_three_forms(alpha):
    rows = alpha.record().parse_laws()
    assert [(r["kind"], r["section"], r["statement"]) for r in rows] == [
        ("law", "Rules for everyone",
         "An inherited claim is a hypothesis wearing a fact's clothes"),
        ("law", "Rules for everyone", "A gate raises and never asserts"),
        ("law", "Rules for everyone",
         "A claim about E03 carries no attribution here"),
        ("rule", "Rules for an executor", "Never judge whether output is good"),
        ("rule", "Rules for an executor", "State a prediction before you look"),
        ("rule", "Rules for an executor",
         "Stop at every gate and never improvise past one"),
        ("law", "Constraints", "Big binaries stay out of git"),
        ("law", "Constraints", "Scripts create their own output directories"),
    ]


def test_a_numbered_bold_item_is_a_rule_and_a_bulleted_one_is_a_law(alpha):
    kinds = {r["statement"]: r["kind"] for r in alpha.record().parse_laws()}
    assert kinds["Never judge whether output is good"] == "rule"
    assert kinds["Big binaries stay out of git"] == "law"


def test_the_attribution_pattern_is_the_repos_own_and_the_gap_is_counted(alpha):
    """ONE OF THE TWO SILENT FAILURES THE EXTRACTION WAS HALTED OVER: a repo
    whose declared range does not match its own arcs gets NULL on every law and
    no error anywhere. alpha declares E01-E02 and one law cites E03 alone."""
    rec = alpha.record()
    paid = {r["statement"]: r["paid_for_by"] for r in rec.parse_laws()}
    assert paid["An inherited claim is a hypothesis wearing a fact's clothes"] == "E01"
    assert paid["A gate raises and never asserts"] == "E02"
    assert paid["A claim about E03 carries no attribution here"] is None
    v = rec.vocab.get("law paid_for_by")
    assert v.recognised == 2 and v.unrecognised == 1
    assert v.samples[0][0] == "E03"


def test_a_repo_declaring_no_attribution_pattern_creates_no_such_vocabulary(beta):
    """beta declares the pattern empty. Every law's attribution is null BY
    DECLARATION, so there is nothing to count and no counter is created - which
    is different from a counter reading zero."""
    rec = beta.record()
    rows = rec.parse_laws()
    assert rows and all(r["paid_for_by"] is None for r in rows)
    assert "law paid_for_by" not in [v.name for v in rec.vocab]


# ---------------------------------------------------------------------------
# experiments
# ---------------------------------------------------------------------------

def test_the_table_is_the_authored_source_and_disk_supplements_it(alpha):
    rows = {r["id"]: r for r in alpha.record().parse_experiments()}
    assert sorted(rows) == ["E01", "E02", "E03"]
    assert rows["E01"]["question"] == "does the control sequence hold across a turn"
    assert rows["E01"]["verdict"] == "RULED"
    assert rows["E01"]["spec_file"] == "docs/experiments/E01-executor-kickoff.md"
    assert rows["E01"]["report_file"] is None
    assert rows["E02"]["report_file"] == "docs/experiments/E02-report.md"
    assert rows["E02"]["spec_file"] is None


def test_a_status_carrying_no_declared_word_is_counted_not_filed(alpha):
    """A SECOND verdict vocabulary, distinct from the rulings' one."""
    rec = alpha.record()
    rows = {r["id"]: r for r in rec.parse_experiments()}
    assert rows["E03"]["verdict"] is None
    v = rec.vocab.get("experiment status")
    assert (v.recognised, v.unrecognised) == (2, 1)


def test_a_repo_with_no_experiments_table_takes_its_rows_from_disk(beta):
    """Not an error. The rows come from disk alone and the absence is reported
    rather than raised on."""
    rows = {r["id"]: r for r in beta.record().parse_experiments()}
    assert sorted(rows) == ["A01", "A02"]
    assert rows["A01"]["question"] is None
    assert rows["A02"]["report_file"] == "record/arcs/A02-report.md"


def test_the_spec_fragments_are_patterns_and_are_the_repos_own(alpha, beta):
    """LIFTED from a function body, and they are PATTERNS rather than
    substrings: the original alternation carried `-E\\d`, which is a regex.
    alpha's fragments find a kickoff; beta's find nothing here, which is beta's
    fact and not a defect."""
    a, b = alpha.record(), beta.record()
    assert a._is_spec_file("E01-executor-kickoff.md")
    assert not a._is_spec_file("E02-report.md")
    assert b._is_spec_file("A01-executor-brief.md")
    assert not b._is_spec_file("A01-executor-kickoff.md")


# ---------------------------------------------------------------------------
# handoffs, and the inverse discovery guard
# ---------------------------------------------------------------------------

def test_handoffs_carry_their_commits_dates_and_superseded_flag(alpha):
    rows = alpha.record().parse_handoffs()
    assert [(r["arc"], r["number"]) for r in rows] == [("E01", 1), ("E01", 2)]
    assert rows[0]["commits"] == "a1b2c3d,deadbee"
    assert rows[0]["date"] == "2026-01-04"
    assert rows[0]["superseded"] == 0
    assert rows[1]["commits"] is None
    assert rows[1]["superseded"] == 1


def test_the_superseded_flag_is_read_from_the_header_line_only(alpha):
    """The flag is `SUPERSEDED in ls[i]` - the header itself. A body mentioning
    the word must not set it, or every handoff discussing supersession marks
    itself."""
    rows = alpha.record().parse_handoffs()
    assert "SUPERSEDED" in rows[1]["outcome"]
    assert rows[0]["superseded"] == 0


def test_a_handoff_header_the_glob_cannot_reach_raises_an_andon(
        alpha, copy_fixture):
    """THE INVERSE GUARD. A discovery rule that only reports what it FOUND
    cannot report what it MISSED, so this asks the opposite question: does any
    file carry a handoff header the glob does not reach."""
    root = copy_fixture("alpha")
    stray = os.path.join(root, "docs", "experiments", "E09-ZZ-stray.md")
    with io.open(stray, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# a stray dispatch\n\n"
                 "## Session handoff 1 (2026-01-01, executor) — invisible\n\n"
                 "It matches neither declared glob, so its dispatch would be "
                 "invisible to the handoffs table and to verify's counts.\n")
    rec = Record(root, alpha.conv)
    with pytest.raises(AssertionError) as exc:
        rec.parse_handoffs()
    assert "ANDON:" in str(exc.value)
    assert "E09-ZZ-stray.md" in str(exc.value)


def test_the_inverse_guard_is_silent_on_a_clean_tree(alpha):
    """CAN-FAIL LEG. Without it, the raise above could pass on a guard that
    fires on everything."""
    rec = alpha.record()
    rec.assert_no_undiscovered_handoffs(rec.handoff_documents())


# ---------------------------------------------------------------------------
# decisions
# ---------------------------------------------------------------------------

def test_a_profiles_registry_is_indexed_not_re_derived(alpha):
    rows = {(r["tool"], r["key"]): r for r in alpha.record().parse_decisions()}
    assert sorted(rows) == [("_still_suspended", "backdrop_word"),
                            ("turn_render", "_calibrated_on"),
                            ("turn_render", "elevation"),
                            ("turn_render", "views")]
    assert rows[("turn_render", "views")]["ruling"] == "E01 Ruling 1"
    assert rows[("turn_render", "_calibrated_on")]["status"] == "marker"


def test_a_status_label_is_read_only_from_the_head_of_the_prose(alpha):
    """Anywhere ELSE in the prose the same words are narrative about the past,
    and reading them as status inverts their meaning: an earlier version
    scanned the whole string and labelled three entries UNDECIDED whose `why`
    says the opposite."""
    rec = alpha.record()
    rows = {(r["tool"], r["key"]): r for r in rec.parse_decisions()}
    assert rows[("turn_render", "views")]["status"] == "DECIDED"
    assert rows[("_still_suspended", "backdrop_word")]["status"] == "SUSPENDED"
    # this one says "closed" mid-sentence and is not labelled by it
    assert rows[("turn_render", "elevation")]["status"] == "decided"


def test_a_repo_declaring_no_profiles_gets_zero_rows_and_no_error(beta):
    assert beta.record().parse_decisions() == []


# ---------------------------------------------------------------------------
# artifacts
# ---------------------------------------------------------------------------

def test_artifacts_are_extracted_by_path_shape_with_a_locality_heuristic(alpha):
    rec = alpha.record()
    rows = {r["path"]: r for r in rec.parse_artifacts(rec.parse_rulings())}
    assert sorted(rows) == ["outputs/e01/depth.png", "outputs/e01/manifest.json",
                            "outputs/e02/bridge.glb", "outputs/e02/sheet.png"]
    assert rows["outputs/e01/depth.png"]["kind"] == "render"
    assert rows["outputs/e01/depth.png"]["provenance_ruling"] == "Ruling 1a"
    assert rows["outputs/e02/bridge.glb"]["mentions"] == 2


def test_an_extension_the_declaration_does_not_carry_is_dropped_and_counted(alpha):
    """THE SILENT DROP, now counted. Six video mentions once vanished from a
    record whose entire product is video, because the extension map had no video
    entry - and an empty table looked exactly like a table that had discarded
    them."""
    rec = alpha.record()
    rows = {r["path"] for r in rec.parse_artifacts(rec.parse_rulings())}
    assert "outputs/e01/turn.mp4" not in rows
    v = rec.vocab.get("artifact kinds")
    assert v.unrecognised == 1
    assert v.samples[0][0] == ".mp4"
    assert "E01-ruling.md" in v.samples[0][1], "the miss does not name a site"


def test_a_complete_extension_map_drops_nothing_and_the_counter_reads_zero(beta):
    """THE ZERO SIDE. beta's map carries every extension its record uses,
    including the video ones alpha's is missing."""
    rec = beta.record()
    rows = {r["path"]: r["kind"] for r in rec.parse_artifacts(rec.parse_rulings())}
    assert rows["outputs/a01/route.mp4"] == "video"
    assert rows["outputs/a02/second.mkv"] == "video"
    assert rec.vocab.get("artifact kinds").unrecognised == 0


# ---------------------------------------------------------------------------
# phenomena
# ---------------------------------------------------------------------------

def test_a_phenomenon_is_found_by_a_declared_naming_verb(alpha):
    rec = alpha.record()
    rows = rec.parse_phenomena(rec.parse_rulings())
    assert len(rows) == 1
    assert rows[0]["marker"] == "banked"
    assert rows[0]["file"] == "docs/experiments/E02-offsurface-ruling.md"


def test_the_residual_population_excludes_what_the_verdicts_already_claim(alpha):
    """Subtracting the declared verdicts is what keeps this counter from
    reporting every `is ACCEPTED` as a phenomenon the tool failed to recognise -
    it is a verdict, recognised by the vocabulary next door."""
    rec = alpha.record()
    rec.parse_phenomena(rec.parse_rulings())
    v = rec.vocab.get("phenomenon markers")
    assert v.recognised == 1
    assert [t for t, _ in v.samples] == ["CORRECTED", "MEASURED"]
    assert "ACCEPTED" not in [t for t, _ in v.samples]


def test_a_repo_declaring_no_markers_gets_no_phenomena_and_no_counter(beta):
    rec = beta.record()
    assert rec.parse_phenomena(rec.parse_rulings()) == []
    assert "phenomenon markers" not in [v.name for v in rec.vocab]


# ---------------------------------------------------------------------------
# prose
# ---------------------------------------------------------------------------

def test_a_file_a_structured_table_owns_is_not_also_indexed_as_prose(alpha):
    """A holding must not be indexed twice under two identities, or the two
    compete in the ranking."""
    rec = alpha.record()
    rulings = rec.parse_rulings()
    structured = {r["file"] for r in rulings}
    prose = rec.parse_prose(structured)
    assert structured
    assert not (structured & {r["file"] for r in prose})


def test_a_handoff_section_is_owned_and_its_document_still_yields_prose(alpha):
    """The kickoff's `## Session handoff` blocks belong to the handoffs table,
    so they are skipped; its preamble is nobody's and is indexed."""
    rec = alpha.record()
    rows = [r for r in rec.parse_prose({r["file"] for r in rec.parse_rulings()})
            if r["file"] == "docs/experiments/E01-executor-kickoff.md"]
    assert [r["anchor"] for r in rows] == ["(preamble)"]


def test_prose_sections_come_out_in_file_then_line_order(alpha):
    rows = alpha.record().parse_prose(set())
    keys = [(r["file"], r["line"]) for r in rows]
    assert keys == sorted(keys)


def test_a_section_shorter_than_the_minimum_is_not_indexed_on_its_own(alpha,
                                                                     tmp_path):
    root = str(tmp_path / "tiny")
    shutil.copytree(alpha.root, root)
    p = os.path.join(root, "docs", "handbook", "index.md")
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# t\n\n## short\n\ntiny.\n")
    rec = Record(root, alpha.conv)
    rows = [r for r in rec.parse_prose(set())
            if r["file"] == "docs/handbook/index.md"]
    assert rows == []


# ---------------------------------------------------------------------------
# the declaration's own audit, both directions
# ---------------------------------------------------------------------------

def test_a_declared_corpus_that_is_absent_is_reported_and_not_raised_on(alpha):
    """THREE PARSERS USED TO RAISE FileNotFoundError on a file list belonging to
    a different repo, which is how the extraction found out the lists were
    repo-specific in the first place."""
    rec = alpha.record()
    rows = rec.parse_prose(set())
    assert rows, "the parser stopped instead of skipping the absent file"
    assert ("declared-but-absent", "corpora.prose_files",
            "docs/absent-by-declaration.md") in rec.corpus_findings


def test_an_undeclared_corpus_that_is_present_is_reported_too(beta):
    """Only reporting BOTH directions makes a declaration auditable. A
    declaration that can report what it named and not what it missed is the
    hardcoded-list defect wearing a different hat. This half is derived from
    the walk rather than accumulated, so it needs no prior build."""
    findings = beta.record().audit_declaration()
    assert sorted(f[2] for f in findings if f[0] == "undeclared-but-present") == [
        "live/status.md", "loose/stray.md"]


def test_alphas_audit_finds_one_thing_and_it_is_the_absent_declaration(
        alpha, tmp_path):
    """The audit reports what a BUILD found, so it is read from the Record that
    did one. A Record that has parsed nothing has found nothing, which is
    correct rather than clean."""
    rec = alpha.record()
    assert rec.audit_declaration() == []
    alpha.build(str(tmp_path / "a.db"), quiet=True, rec=rec)
    assert rec.audit_declaration() == [
        ("declared-but-absent", "corpora.prose_files",
         "docs/absent-by-declaration.md")]


# ---------------------------------------------------------------------------
# a Record is per-build
# ---------------------------------------------------------------------------

def test_each_call_to_record_hands_back_a_fresh_one(alpha):
    """DELIBERATE: a Record carries this build's findings and vocabulary
    counters. Reusing one accumulates counts across builds, which is the
    module-level accumulator defect this package's own docstrings say was not
    carried forward."""
    a, b = alpha.record(), alpha.record()
    assert a is not b
    a.parse_rulings()
    assert a.vocab.get("ruling headers").recognised == 6
    assert b.vocab.get("ruling headers").recognised == 0


def test_one_record_used_twice_accumulates_and_that_is_why_it_is_per_build(alpha):
    """The measurement behind the rule above, pinned so it stays visible: parse
    twice on ONE Record and every counter doubles."""
    rec = alpha.record()
    rec.parse_rulings()
    once = rec.vocab.get("ruling headers").recognised
    rec.parse_rulings()
    assert rec.vocab.get("ruling headers").recognised == 2 * once


# ---------------------------------------------------------------------------
# FINDING - the sub-ruling locator is not derived from the declaration
# ---------------------------------------------------------------------------

def _relettered_copy(root, conv_doc, sub_pattern, old_new):
    doc = json.loads(json.dumps(conv_doc))
    doc["headers"]["sub_ruling"] = sub_pattern
    p = os.path.join(root, "docs", "experiments", "E01-ruling.md")
    with io.open(p, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in old_new:
        src = src.replace(old, new)
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    return Record(root, Conventions(doc))


@pytest.mark.xfail(strict=True, reason=(
    "FINDING. `headers.sub_ruling` is a declared convention, but the locator a "
    "sub-ruling row carries is built in parse.py as the literal "
    "'**%s%s ' % (num, letter) — the alpha/facet form, hard-coded. A repo that "
    "legally declares any other sub-ruling marker therefore gets rows whose "
    "locator string does not occur in its own file, and verify leg 3 reports "
    "them as dangling pointers produced by the tool rather than by the record. "
    "Evidence: with headers.sub_ruling declared as '^\\\\*\\\\*(\\\\d+)\\\\.([a-z])\\\\s+[—–-]' "
    "and the fixture written as '**1.a — ', the row's locator is '**1a ', which "
    "is absent from the document. Same for sub_closure."))
def test_a_declared_sub_ruling_marker_produces_a_findable_locator(
        alpha, alpha_conv, copy_fixture):
    root = copy_fixture("alpha")
    rec = _relettered_copy(root, alpha_conv.doc,
                           r"^\*\*(\d+)\.([a-z])\s+[—–-]",
                           [("**1a — ", "**1.a — "), ("**1b — ", "**1.b — ")])
    src = rec.read("docs/experiments/E01-ruling.md")
    subs = [r for r in rec.parse_rulings() if r["kind"] == "sub-ruling"]
    assert subs, "the re-lettered fixture parsed no sub-rulings at all"
    for r in subs:
        assert r["locator"] in src, (
            "locator %r is not in the file; the declared marker is %r"
            % (r["locator"], rec.conv.sub_ruling_re.pattern))
