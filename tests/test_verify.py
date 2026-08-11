"""verify - four legs that GATE, and two sections that report.

A DIAGNOSTIC AND A GATE ARE DIFFERENT OBJECTS. Legs 1 to 4 decide the exit code.
The declaration audit and the vocabulary report do not, and alpha is built so
that both of them have something to say on a run that must still exit 0 - which
is the only way to tell a report from a gate by measurement rather than by
reading the comment above it.

THE TRANSCRIPT IS A CONTRACT: other tools parse this output into a certificate
and the LAST NON-EMPTY LINE is the verdict. Anything added to the transcript is
printed before the verdict block, and that ordering is pinned here.
"""
import io
import json
import os
import re
import sqlite3

import pytest

import record_index
from record_index import index as I
from record_index.conventions import Conventions
from record_index.parse import Record


def _tail(out):
    return [ln for ln in out.split("\n") if ln.strip()][-1]


def _edit(root, rel, old, new):
    p = os.path.join(root, rel.replace("/", os.sep))
    with io.open(p, encoding="utf-8") as fh:
        src = fh.read()
    assert old in src, "the fixture edit found nothing to replace: %r" % old
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src.replace(old, new))


# ---------------------------------------------------------------------------
# the clean run
# ---------------------------------------------------------------------------

def test_alpha_passes_all_four_legs(alpha, alpha_db, capsys):
    assert alpha.verify(alpha_db) == I.EXIT_OK
    out = capsys.readouterr().out
    assert "VERIFY PASSED - all four legs" in out
    assert "4 / 4" in out


def test_beta_passes_all_four_legs(beta, beta_db, capsys):
    """A verify that only ever ran on one corpus is a verify tuned to one
    corpus's shape."""
    assert beta.verify(beta_db) == I.EXIT_OK
    assert "VERIFY PASSED" in capsys.readouterr().out


def test_the_last_non_empty_line_is_the_verdict(alpha, alpha_db, capsys):
    alpha.verify(alpha_db)
    assert _tail(capsys.readouterr().out) == "VERIFY PASSED - all four legs"


def test_the_verdict_is_the_last_line_on_a_failing_run_too(alpha, alpha_db,
                                                           tmp_path, capsys):
    """The contract has to hold on the run a caller most needs to parse."""
    broken = str(tmp_path / "broken.db")
    with open(alpha_db, "rb") as fh:
        data = fh.read()
    with open(broken, "wb") as fh:
        fh.write(data)
    con = sqlite3.connect(broken)
    con.execute("DELETE FROM rulings WHERE kind='ruling' AND arc='E01'")
    con.commit()
    con.close()
    assert alpha.verify(broken) == I.EXIT_REFUSED
    out = capsys.readouterr().out
    assert _tail(out).startswith("  X ") or "VERIFY FAILED" in out
    assert "VERIFY FAILED" in out


def test_the_diagnostics_are_printed_before_the_verdict_block(alpha, alpha_db,
                                                              capsys):
    alpha.verify(alpha_db)
    out = capsys.readouterr().out
    assert out.index("[vocabulary]") < out.index("VERIFY PASSED")
    assert out.index("[declaration]") < out.index("[vocabulary]")
    assert out.index("[leg 4]") < out.index("[declaration]")


def test_the_determinism_leg_names_which_form_of_identity_held(alpha, alpha_db,
                                                               capsys):
    alpha.verify(alpha_db)
    out = capsys.readouterr().out
    assert "determinism leg that held:" in out
    assert ("BYTE-IDENTICAL" in out) or ("DUMP-IDENTICAL" in out)


def test_the_determinism_temp_files_are_removed(alpha, alpha_db, tmp_path):
    alpha.verify(alpha_db)
    leftovers = [p for p in os.listdir(str(tmp_path))
                 if ".det_a." in p or ".det_b." in p]
    assert leftovers == []


def test_verify_closes_its_handle_so_a_build_can_follow_it(alpha, alpha_db):
    """Harmless in a CLI - the process ends a millisecond later - but a
    long-lived server calls verify and then build in one interpreter, and build
    starts with os.remove(db_path). On Windows a removal fails while any handle
    is open."""
    alpha.verify(alpha_db)
    alpha.build(alpha_db, quiet=True)


# ---------------------------------------------------------------------------
# the diagnostics report and do not gate
# ---------------------------------------------------------------------------

def test_a_run_with_unrecognised_vocabulary_still_exits_zero(alpha, alpha_db,
                                                             capsys):
    """alpha's declaration is deliberately short: three shouted verbs it does
    not claim, one extension it drops, one law attribution it misses, one
    experiment status it cannot read. All of that is REPORTED and none of it
    gates."""
    rc = alpha.verify(alpha_db)
    out = capsys.readouterr().out
    assert rc == I.EXIT_OK
    assert "total unrecognised inputs: 0" not in out
    assert "not recognised: BANKED, CORRECTED, MEASURED" in out
    assert "not recognised: .mp4" in out


def test_a_declaration_finding_still_exits_zero(alpha, alpha_db, capsys):
    rc = alpha.verify(alpha_db)
    out = capsys.readouterr().out
    assert rc == I.EXIT_OK
    assert "declared-but-absent" in out
    assert "docs/absent-by-declaration.md" in out
    assert "REPORT ONLY" in out


def test_the_mechanism_calibration_rides_the_transcript(alpha, alpha_db, capsys):
    """A number quoted from a run carries the corpus it was fit to, or a reader
    cannot tell a default from a measurement about their own record."""
    alpha.verify(alpha_db)
    assert "calibrated on facet@2026-08" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# leg 2 - counts
# ---------------------------------------------------------------------------

def test_a_count_mismatch_fails_leg_two_and_refuses(alpha, alpha_db, tmp_path,
                                                    capsys):
    broken = str(tmp_path / "broken.db")
    with open(alpha_db, "rb") as fh:
        data = fh.read()
    with open(broken, "wb") as fh:
        fh.write(data)
    con = sqlite3.connect(broken)
    con.execute("DELETE FROM rulings WHERE arc='E01' AND number='2' "
                "AND kind='ruling'")
    con.commit()
    con.close()

    assert alpha.verify(broken) == I.EXIT_REFUSED
    out = capsys.readouterr().out
    assert "MISMATCH" in out
    assert "count E01 numbered rulings: grep 2 != db 1" in out


def test_a_sequence_gap_fails_and_names_the_missing_numbers(alpha, alpha_conv,
                                                            tmp_path, capsys):
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["verify"]["sequences"] = [["E01", "ruling", 1, 4]]
    doc["verify"]["count_checks"] = []
    conv = Conventions(doc)
    rec = Record(alpha.root, conv)
    db = str(tmp_path / "gap.db")
    I.build(rec, db, quiet=True)
    assert I.verify(Record(alpha.root, conv), db) == I.EXIT_REFUSED
    assert "E01 ruling sequence gaps [3, 4]" in capsys.readouterr().out


def test_a_record_above_a_declared_bound_is_a_note_and_not_a_failure(
        alpha, alpha_conv, tmp_path, capsys):
    """Ranges are as DECLARED, not as measured. A record carrying more than a
    bound prints as a completeness note rather than silently widening the gate -
    and it must not fail, or a bound could never be a pre-registration."""
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["verify"]["sequences"] = [["E01", "ruling", 1, 1]]
    doc["verify"]["count_checks"] = []
    conv = Conventions(doc)
    rec = Record(alpha.root, conv)
    db = str(tmp_path / "over.db")
    I.build(rec, db, quiet=True)
    assert I.verify(Record(alpha.root, conv), db) == I.EXIT_OK
    out = capsys.readouterr().out
    assert "ABOVE the declared bound of 1: [2]" in out
    assert "the bound stays as declared" in out


def test_unexpected_handoff_coverage_fails(alpha, alpha_conv, tmp_path, capsys):
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["verify"]["handoff_coverage"] = {"arc": "E01", "lo": 1, "hi": 4,
                                         "expect_missing": []}
    doc["verify"]["count_checks"] = []
    conv = Conventions(doc)
    db = str(tmp_path / "hc.db")
    I.build(Record(alpha.root, conv), db, quiet=True)
    assert I.verify(Record(alpha.root, conv), db) == I.EXIT_REFUSED
    assert "handoff coverage unexpected" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# leg 3 - pointers
# ---------------------------------------------------------------------------

def test_a_locator_that_no_longer_occurs_is_a_dangling_pointer(
        alpha, copy_fixture, tmp_path, capsys):
    """The gate that makes an anchor a promise rather than a label. The corpus
    is edited AFTER the build, so exactly one locator stops resolving and every
    count still agrees."""
    root = copy_fixture("alpha")
    rec = Record(root, alpha.conv)
    db = str(tmp_path / "d.db")
    I.build(rec, db, quiet=True)
    _edit(root, "docs/experiments/E01-ruling.md",
          "> ### Amendment 1 (", "> ### Amendment 01 (")

    assert I.verify(Record(root, alpha.conv), db) == I.EXIT_REFUSED
    out = capsys.readouterr().out
    assert "rulings: 1 dangling pointers" in out
    assert "MISMATCH" not in out, "the edit was meant to move only leg 3"


def test_leg_three_reports_zero_on_the_untouched_corpus(alpha, alpha_db, capsys):
    """CAN-FAIL LEG for the check above: the same code path on an unedited
    corpus must find nothing."""
    alpha.verify(alpha_db)
    out = capsys.readouterr().out
    assert "total checked 33, dangling 0" in out


def test_a_row_from_a_file_the_glob_does_not_discover_fails(alpha, alpha_db,
                                                            tmp_path, capsys):
    """A discovery rule that only reports what it found cannot report what it
    missed - so verify asks the inverse question of the DATABASE too."""
    broken = str(tmp_path / "orphan.db")
    with open(alpha_db, "rb") as fh:
        data = fh.read()
    with open(broken, "wb") as fh:
        fh.write(data)
    con = sqlite3.connect(broken)
    con.execute("UPDATE rulings SET file='docs/experiments/E99-nope.md' "
                "WHERE arc='E02' AND number='1'")
    con.commit()
    con.close()
    assert alpha.verify(broken) == I.EXIT_REFUSED
    out = capsys.readouterr().out
    assert "ROWS FROM UNDISCOVERED FILES" in out
    assert "E99-nope.md" in out


# ---------------------------------------------------------------------------
# leg 4 - the seeded set
# ---------------------------------------------------------------------------

def test_a_seeded_question_whose_target_is_unreachable_fails(alpha, alpha_conv,
                                                             tmp_path, capsys):
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["verify"]["seeded"] = [
        ["a question nothing answers", "the depth pass normalization",
         ["docs/experiments/E02-report.md", "What was measured"]]]
    conv = Conventions(doc)
    db = str(tmp_path / "s.db")
    I.build(Record(alpha.root, conv), db, quiet=True)
    assert I.verify(Record(alpha.root, conv), db) == I.EXIT_REFUSED
    out = capsys.readouterr().out
    assert "seeded question MISS: a question nothing answers" in out
    assert "got 1." in out, "a miss must print what it got instead"


def test_a_seed_with_no_anchor_matches_any_anchor_in_the_file(alpha, alpha_db,
                                                              capsys):
    """alpha's fourth seed targets CLAUDE.md with a null anchor, which is the
    `wa is None` branch - a question whose right answer is a document rather
    than a row."""
    assert alpha.verify(alpha_db) == I.EXIT_OK
    assert "(any anchor)" in capsys.readouterr().out


def test_the_top_n_is_a_parameter_of_the_leg(alpha, alpha_conv, tmp_path,
                                             capsys):
    """A seed whose target ranks 2 must HIT at top_n=3 and MISS at top_n=1.
    Without both halves, the leg could be checking presence anywhere in the
    result set rather than rank, and every seeded question would pass as long as
    its target existed at all."""
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["verify"]["seeded"] = [
        ["the phenomenon's sibling", "off-surface margin banked measured phenomenon",
         ["docs/experiments/E02-offsurface-ruling.md", "Ruling 2"]]]
    conv = Conventions(doc)
    db = str(tmp_path / "rank.db")
    I.build(Record(alpha.root, conv), db, quiet=True)

    assert I.verify(Record(alpha.root, conv), db, top_n=3) == I.EXIT_OK
    assert "rank 2" in capsys.readouterr().out
    assert I.verify(Record(alpha.root, conv), db, top_n=1) == I.EXIT_REFUSED
    assert "seeded question MISS: the phenomenon's sibling" in \
        capsys.readouterr().out


# ---------------------------------------------------------------------------
# MEASURED: verify reuses one Record across its two builds
# ---------------------------------------------------------------------------

def _one_build_counts(binding, tmp_path):
    rec = binding.record()
    I.build(rec, str(tmp_path / "once.db"), quiet=True)
    return ({v.name: (v.recognised, v.unrecognised) for v in rec.vocab},
            len(rec.audit_declaration()))


TRANSCRIPT_ROW = re.compile(
    r"^ {2}(\S.*?)\s+recognised\s+(\d+)\s+unrecognised\s+(\d+)\s*$")


def _transcript_counts(out):
    got = {}
    for ln in out.split("\n"):
        m = TRANSCRIPT_ROW.match(ln)
        if m:
            got[m.group(1).strip()] = (int(m.group(2)), int(m.group(3)))
    assert got, "no vocabulary rows were found in the transcript at all"
    return got


@pytest.mark.xfail(strict=True, reason=(
    "FINDING. `Record.record()` hands back a FRESH Record per call precisely so "
    "that vocabulary counters and corpus findings do not accumulate across "
    "builds - the docstring names `verify` builds three times in one process as "
    "the reason. But `verify()` itself passes ONE Record to both of leg 1's "
    "builds, so every number in the transcript's two diagnostic sections is "
    "exactly DOUBLE the corpus's real count. Measured on alpha: one build "
    "reports verdicts 4/3, artifact kinds 5/1, law paid_for_by 2/1, experiment "
    "status 2/1, phenomenon markers 1/2, ruling headers 6/0, total unrecognised "
    "8, and 1 declaration finding; verify's transcript reports 8/6, 10/2, 4/2, "
    "4/2, 2/4, 12/0, total 16, and the same finding listed twice."))
def test_the_transcript_reports_the_corpus_counts_not_twice_the_corpus_counts(
        alpha, alpha_db, tmp_path, capsys):
    want, want_findings = _one_build_counts(alpha, tmp_path)
    alpha.verify(alpha_db)
    out = capsys.readouterr().out
    assert _transcript_counts(out) == want
    assert "%d finding(s)" % want_findings in out


def test_the_doubling_is_exactly_two_and_the_gates_are_untouched_by_it(
        alpha, alpha_db, tmp_path, capsys):
    """THE SAME MEASUREMENT, pinned as behaviour rather than as a wish, so the
    finding above has a number attached and so a change to it is visible. The
    accumulation is in the two REPORT-ONLY sections; every gating leg reads the
    database and is unaffected, and the run still exits 0."""
    want, want_findings = _one_build_counts(alpha, tmp_path)
    rc = alpha.verify(alpha_db)
    out = capsys.readouterr().out
    got = _transcript_counts(out)
    assert rc == I.EXIT_OK
    assert got == {k: (r * 2, u * 2) for k, (r, u) in want.items()}
    assert "%d finding(s)" % (want_findings * 2) in out


# ---------------------------------------------------------------------------
# MEASURED: a count check naming a file that is not on disk
# ---------------------------------------------------------------------------

def test_a_count_check_naming_an_absent_file_raises_rather_than_failing_a_leg(
        alpha, alpha_conv, tmp_path):
    """PINNED AS MEASURED, not as approved. A DECLARED CORPUS that is absent is
    skipped and reported - that is the ruled behaviour and test_parse covers it.
    A `verify.count_checks` leg naming an absent file is a different path: it
    goes through `rec.lines_of` and raises FileNotFoundError, which the CLI
    reports as a runtime error (exit 2) rather than as a refusal (exit 4).
    test_cli pins the exit code that reaches an operator."""
    doc = json.loads(json.dumps(alpha_conv.doc))
    doc["verify"]["count_checks"] = [
        ["a leg naming nothing", "docs/experiments/E77-absent.md",
         "^## Ruling", "rulings", "arc='E01'"]]
    conv = Conventions(doc)
    db = str(tmp_path / "cc.db")
    I.build(Record(alpha.root, conv), db, quiet=True)
    with pytest.raises(FileNotFoundError):
        I.verify(Record(alpha.root, conv), db)


# ---------------------------------------------------------------------------
# the binding surface
# ---------------------------------------------------------------------------

def test_verify_builds_from_the_record_and_never_writes_the_index_it_checks(
        alpha, alpha_db):
    """Leg 1 builds into per-process temp paths beside the index; the index
    under test is opened read-and-never-written. Its bytes must be unchanged by
    a verify."""
    with open(alpha_db, "rb") as fh:
        before = fh.read()
    alpha.verify(alpha_db)
    with open(alpha_db, "rb") as fh:
        assert fh.read() == before


def test_two_verifies_in_one_working_copy_do_not_collide(alpha, alpha_db):
    """The temp paths are per-process unique in the same directory: two
    verifies in one working copy once wrote the same two fixed files and could
    read each other's bytes mid-build."""
    assert alpha.verify(alpha_db) == I.EXIT_OK
    assert alpha.verify(alpha_db) == I.EXIT_OK


def test_a_binding_verifies_through_a_fresh_record_each_time(alpha, alpha_db,
                                                             capsys):
    alpha.verify(alpha_db)
    first = _transcript_counts(capsys.readouterr().out)
    alpha.verify(alpha_db)
    assert _transcript_counts(capsys.readouterr().out) == first, (
        "a second verify in the same process reported different counts, so the "
        "Record was shared between them")


def test_record_index_exposes_the_verify_verb_through_the_binding(alpha):
    assert record_index.Binding(alpha.root, alpha.conv).verify.__self__ is not None
