"""certificate.py - the db and its certificate move together or not at all.

A BUILD WITHOUT ITS VERIFY IS THE UNGATED STATE THIS EXISTS TO CLOSE. Measured
the hard way in the repo this came from, where `build` and `verify` were separate
verbs and a fresh db could sit beside a stale certificate indefinitely, reading
as verified.

THE CERTIFICATE DESCRIBES ONE ARTIFACT. It carries the db's size and digest, so a
certificate found beside a DIFFERENT index is detected rather than trusted - and
that is what makes `verified` a property of the bytes present rather than of a
file having once existed. Every state below is reached by producing the condition
it names, never by hand-writing the state string, except where the condition IS a
tampered certificate.
"""
import io
import json
import os
import sqlite3
import sys

import pytest

import record_index
from record_index import certificate as CERT
from record_index import index as I
from record_index.conventions import Conventions


@pytest.fixture
def staged(copy_fixture):
    """A copied corpus and a db path inside it: (root, binding, db_path)."""
    def _stage(name="alpha"):
        root = copy_fixture(name)
        conv = record_index.conventions.load(
            os.path.join(root, "docs", "index", "conventions.json")
            if name == "alpha" else os.path.join(root, "index", "conventions.json"))
        b = record_index.Binding(root, conv)
        return root, b, os.path.join(root, conv.db_rel.replace("/", os.sep))
    return _stage


def _read_cert(db):
    with io.open(CERT.cert_path(db), encoding="utf-8") as fh:
        return json.load(fh)


def _write_cert(db, doc):
    with io.open(CERT.cert_path(db), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# one verb: build, verify, certify
# ---------------------------------------------------------------------------

def test_build_and_certify_writes_the_pair_and_returns_the_document(staged):
    root, b, db = staged()
    doc = CERT.build_and_certify(b, db)
    assert os.path.exists(db)
    assert os.path.exists(CERT.cert_path(db))
    assert doc["schema"] == CERT.CERT_SCHEMA
    assert doc["repo"] == "alpha"
    assert doc["state"] == "PASSED"
    assert doc["verify_exit_code"] == I.EXIT_OK
    assert doc == _read_cert(db)


def test_there_is_no_path_that_writes_a_db_without_a_certificate_for_it(staged):
    """The verb is one verb. A caller cannot get the db half on its own from
    here, which is the whole point of merging them."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    assert os.path.exists(CERT.cert_path(db))
    os.remove(CERT.cert_path(db))
    CERT.build_and_certify(b, db)
    assert os.path.exists(CERT.cert_path(db))


def test_the_certificate_carries_the_size_and_digest_of_the_db_beside_it(staged):
    root, b, db = staged()
    doc = CERT.build_and_certify(b, db)
    assert doc["db"]["path"] == os.path.basename(db)
    assert doc["db"]["bytes"] == os.path.getsize(db)
    assert doc["db"]["sha256"] == CERT._digest(db)


def test_the_certificate_carries_the_whole_verify_transcript(staged):
    """A caller reads a persisted field rather than a shell's `$?` that nobody
    kept, and the transcript is there so the reason is persisted too."""
    root, b, db = staged()
    doc = CERT.build_and_certify(b, db)
    joined = "\n".join(doc["transcript"])
    assert "record_index verify - four legs" in joined
    assert "VERIFY PASSED" in joined
    assert "[vocabulary]" in joined


def test_certifying_still_prints_the_transcript(staged, capsys):
    """A verb that swallowed its own transcript would make the operator read a
    JSON file to find out what happened."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    assert "VERIFY PASSED" in capsys.readouterr().out


def test_the_tee_restores_stdout_even_when_verify_raises(staged, tmp_path):
    """A capture that leaked would take stdout down for the rest of the
    process, and the failure would surface a long way from its cause."""
    root, b, db = staged()
    doc = json.loads(json.dumps(b.conv.doc))
    doc["verify"]["count_checks"] = [
        ["a leg naming nothing", "docs/experiments/E77-absent.md",
         "^## Ruling", "rulings", "arc='E01'"]]
    broken = record_index.Binding(root, Conventions(doc))
    before = sys.stdout
    with pytest.raises(FileNotFoundError):
        CERT.build_and_certify(broken, db)
    assert sys.stdout is before


def test_a_corpus_that_fails_verify_certifies_as_failed(staged):
    """END TO END rather than by hand-writing a state string: the seeded set is
    given a target nothing answers, so verify refuses and the certificate
    records the refusal."""
    root, b, db = staged()
    doc = json.loads(json.dumps(b.conv.doc))
    doc["verify"]["seeded"] = [
        ["a question nothing answers", "the depth pass normalization",
         ["docs/experiments/E02-report.md", "What was measured"]]]
    failing = record_index.Binding(root, Conventions(doc))
    cert = CERT.build_and_certify(failing, db)
    assert cert["state"] == "FAILED"
    assert cert["verify_exit_code"] == I.EXIT_REFUSED


# ---------------------------------------------------------------------------
# health
# ---------------------------------------------------------------------------

def test_no_index_is_index_missing(staged):
    root, b, db = staged()
    h = CERT.health(b, db)
    assert h["state"] == "INDEX_MISSING"
    assert h["serving"] is False
    assert db in h["why"]


def test_an_index_with_no_certificate_never_serves(staged):
    root, b, db = staged()
    b.build(db, quiet=True)
    h = CERT.health(b, db)
    assert h["state"] == "INDEX_NEVER_VERIFIED"
    assert h["serving"] is False
    assert "no certificate beside" in h["why"]


def test_a_certified_index_serves(staged):
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    h = CERT.health(b, db)
    assert h == {"state": "SERVING", "serving": True, "why": None}


def test_the_second_corpus_serves_too(staged):
    root, b, db = staged("beta")
    CERT.build_and_certify(b, db)
    assert CERT.health(b, db)["state"] == "SERVING"


def test_a_failed_verify_does_not_serve(staged):
    root, b, db = staged()
    doc = json.loads(json.dumps(b.conv.doc))
    doc["verify"]["seeded"] = [
        ["a question nothing answers", "the depth pass normalization",
         ["docs/experiments/E02-report.md", "What was measured"]]]
    failing = record_index.Binding(root, Conventions(doc))
    CERT.build_and_certify(failing, db)
    h = CERT.health(failing, db)
    assert h["state"] == "INDEX_VERIFY_FAILED"
    assert h["serving"] is False


def test_a_certificate_beside_a_different_index_is_detected(staged):
    """WHAT MAKES `verified` A PROPERTY OF THE BYTES PRESENT. The db is edited
    after certification, so the certificate is describing an index that is no
    longer there."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    con = sqlite3.connect(db)
    con.execute("INSERT INTO laws VALUES ('planted','law',NULL,NULL,'x','x','x',1)")
    con.commit()
    con.close()
    h = CERT.health(b, db)
    assert h["state"] == "INDEX_NEVER_VERIFIED"
    assert h["why"] == "the certificate describes a different index"
    assert h["serving"] is False


def test_an_unreadable_certificate_does_not_serve(staged):
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    with io.open(CERT.cert_path(db), "w", encoding="utf-8") as fh:
        fh.write("{ not json at all")
    h = CERT.health(b, db)
    assert h["state"] == "INDEX_NEVER_VERIFIED"
    assert "certificate unreadable" in h["why"]


def test_a_certificate_that_is_not_an_object_does_not_serve(staged):
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    _write_cert(db, ["not", "an", "object"])
    assert CERT.health(b, db)["state"] == "INDEX_NEVER_VERIFIED"


@pytest.mark.parametrize("missing", ["schema", "state", "db", "corpus"])
def test_a_certificate_missing_a_required_key_does_not_serve(staged, missing):
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    doc = _read_cert(db)
    del doc[missing]
    _write_cert(db, doc)
    h = CERT.health(b, db)
    assert h["state"] == "INDEX_NEVER_VERIFIED"
    assert missing in h["why"]


def test_an_unknown_certificate_schema_does_not_serve(staged):
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    doc = _read_cert(db)
    doc["schema"] = "some-other-tool-certificate/1"
    _write_cert(db, doc)
    assert CERT.health(b, db)["state"] == "INDEX_NEVER_VERIFIED"


def test_the_pre_extraction_schema_id_is_still_accepted_on_read(staged):
    """DUAL-ACCEPT ON READ. The writer emits exactly one id; the reader accepts
    the pre-extraction one too, so a certificate written before the rename keeps
    verifying instead of turning a working index into NEVER_VERIFIED on
    upgrade."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    doc = _read_cert(db)
    doc["schema"] = "facet-record-index-certificate/1"
    _write_cert(db, doc)
    assert CERT.health(b, db)["state"] == "SERVING"


def test_the_writer_emits_exactly_one_schema_id(staged):
    root, b, db = staged()
    assert CERT.build_and_certify(b, db)["schema"] == CERT.CERT_SCHEMA
    assert CERT.CERT_SCHEMA in CERT.CERT_SCHEMA_ACCEPTED
    assert len(CERT.CERT_SCHEMA_ACCEPTED) == 2


# ---------------------------------------------------------------------------
# staleness warns rather than refuses
# ---------------------------------------------------------------------------

def test_a_moved_corpus_is_stale_and_still_serves(staged):
    """STALE WARNS RATHER THAN REFUSES, on purpose: the db commits at session
    boundaries and not every fold, so bounded staleness is the ruled normal
    state of a fresh clone. A refusal here would fire on correct work."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    p = os.path.join(root, "CLAUDE.md")
    with io.open(p, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("\nOne more line, folded after the index was built.\n")
    h = CERT.health(b, db)
    assert h["state"] == "STALE"
    assert h["serving"] is True


def test_staleness_names_what_moved(staged):
    """A warning a session cannot act on is a warning it learns to ignore."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    with io.open(os.path.join(root, "CLAUDE.md"), "a", encoding="utf-8",
                 newline="\n") as fh:
        fh.write("\nfolded later\n")
    h = CERT.health(b, db)
    assert h["moved"] == ["CLAUDE.md"]
    assert h["moved_total"] == 1


def test_a_new_document_makes_the_index_stale_too(staged):
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    with io.open(os.path.join(root, "docs", "experiments", "E04-ruling.md"),
                 "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# E04\n\n## Ruling 1 — a later arc IS ACCEPTED\n\n"
                 "Folded after the index was built, so the corpus has moved.\n")
    h = CERT.health(b, db)
    assert h["state"] == "STALE"
    assert "docs/experiments/E04-ruling.md" in h["moved"]


def test_an_untouched_corpus_is_not_stale(staged):
    """CAN-FAIL LEG for the three above. If `corpus_id` were constant, every one
    of them would pass and none would be measuring staleness."""
    root, b, db = staged()
    CERT.build_and_certify(b, db)
    assert CERT.health(b, db)["state"] == "SERVING"


def test_the_certificate_path_is_the_db_path_plus_the_suffix(tmp_path):
    assert CERT.cert_path(str(tmp_path / "x.db")) == \
        str(tmp_path / "x.db") + CERT.CERT_SUFFIX
