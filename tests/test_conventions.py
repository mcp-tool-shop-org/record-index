"""conventions.py - a repo's declaration, and the refusals it makes at load time.

THE PROPERTY UNDER TEST IS THE ABSENCE OF A DEFAULT. Conventions are a full
declaration precisely so that a second repo cannot inherit a first repo's history
by omission, so the checks that matter here are the ones that fire on a field
NOBODY STATED - and they must name the field, at load, rather than surfacing as
an empty table six steps later.

Every fixture below answers: what would this look like if the code were wrong in
the way this check exists to catch? A loader that quietly filled a missing field
would pass a test that only ever loaded a complete declaration, so most of what
is here is deliberately incomplete input.
"""
import copy
import io
import json
import os

import pytest

from conftest import ALPHA, ALPHA_CONV_REL, BETA, BETA_CONV_REL
from record_index.conventions import (CONVENTIONS_SCHEMA, MAY_BE_EMPTY,
                                      REQUIRED_FIELDS, Conventions,
                                      ConventionsError, load)


def _doc(root, rel):
    with io.open(os.path.join(root, rel.replace("/", os.sep)),
                 encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def alpha_doc():
    return _doc(ALPHA, ALPHA_CONV_REL)


@pytest.fixture
def beta_doc():
    return _doc(BETA, BETA_CONV_REL)


def _set(doc, path, value):
    cur = doc
    parts = path.split(".")
    for p in parts[:-1]:
        cur = cur[p]
    cur[parts[-1]] = value


def _drop(doc, path):
    cur = doc
    parts = path.split(".")
    for p in parts[:-1]:
        cur = cur[p]
    del cur[parts[-1]]


# ---------------------------------------------------------------------------
# both fixture declarations load, and they disagree
# ---------------------------------------------------------------------------

def test_both_fixture_declarations_load(alpha_conv, beta_conv):
    assert alpha_conv.name == "alpha"
    assert beta_conv.name == "beta"


def test_the_two_declarations_agree_on_nothing_that_describes_a_document(
        alpha_conv, beta_conv):
    """THE POINT OF THE SECOND REPO. If these fields matched, every later test
    would be right for the same reason and none of them would be telling a
    declared convention from a hard-coded one."""
    assert alpha_conv.markers != beta_conv.markers
    assert alpha_conv.experiments_dir != beta_conv.experiments_dir
    assert alpha_conv.ruling_doc_re.pattern != beta_conv.ruling_doc_re.pattern
    assert alpha_conv.db_rel != beta_conv.db_rel
    assert alpha_conv.db_env != beta_conv.db_env
    assert alpha_conv.authority_named != beta_conv.authority_named
    assert alpha_conv.authority_default != beta_conv.authority_default
    assert set(alpha_conv.verdicts).isdisjoint(beta_conv.verdicts)
    assert set(alpha_conv.artifact_extensions) != set(beta_conv.artifact_extensions)
    # and the arc rules are each other's opposite branch
    assert "strip_from" in alpha_conv.ruling_arc and beta_conv.ruling_arc.get("leading")
    assert alpha_conv.kickoff_arc.get("leading") and "strip_from" in beta_conv.kickoff_arc


# ---------------------------------------------------------------------------
# schema identity
# ---------------------------------------------------------------------------

def test_a_wrong_schema_id_refuses_and_names_both(alpha_doc, tmp_path):
    alpha_doc["schema"] = "record-index-conventions/99"
    p = tmp_path / "c.json"
    p.write_text(json.dumps(alpha_doc), encoding="utf-8")
    with pytest.raises(ConventionsError) as exc:
        load(str(p))
    assert "record-index-conventions/99" in str(exc.value)
    assert CONVENTIONS_SCHEMA in str(exc.value)
    assert str(p) in str(exc.value), "the refusal does not name the file it read"


def test_a_missing_schema_key_refuses(alpha_doc):
    del alpha_doc["schema"]
    with pytest.raises(ConventionsError):
        Conventions(alpha_doc)


def test_a_declaration_that_is_not_an_object_refuses_by_type(tmp_path):
    p = tmp_path / "c.json"
    p.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(ConventionsError) as exc:
        load(str(p))
    assert "JSON object" in str(exc.value) and "list" in str(exc.value)


# ---------------------------------------------------------------------------
# no field has a default - one test per required field
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_every_required_field_refuses_when_it_is_not_declared(alpha_doc, field):
    """THE WHOLE DESIGN, checked field by field. A loader with one silent
    fallback would pass a spot check of three fields and fail here, and the
    fallback would be another repo's history shipped as this repo's default."""
    _drop(alpha_doc, field)
    with pytest.raises(ConventionsError) as exc:
        Conventions(alpha_doc)
    msg = str(exc.value)
    assert field in msg, "the refusal does not name the field: %s" % msg
    assert "not declared" in msg


def test_a_field_that_may_not_be_empty_refuses_when_declared_empty(alpha_doc):
    _set(alpha_doc, "corpora.law_files", [])
    with pytest.raises(ConventionsError) as exc:
        Conventions(alpha_doc)
    assert "declared but empty" in str(exc.value)
    assert "corpora.law_files" in str(exc.value)


@pytest.mark.parametrize("field", sorted(MAY_BE_EMPTY))
def test_a_field_that_may_be_empty_loads_when_declared_empty(alpha_doc, field):
    """`[]` here is a STATEMENT - this repo has none of these - and a loader
    that rejected it would force a repo to declare a value it does not have."""
    empty = {"headers.addenda": [], "headers.amendment": []}.get(field, [])
    _set(alpha_doc, field, empty)
    Conventions(alpha_doc)


def test_an_empty_ruling_header_list_refuses(alpha_doc):
    """A record with no ruling-header form declared can carry no rulings at
    all, which is a declaration error and not an empty table."""
    _set(alpha_doc, "headers.ruling", [])
    with pytest.raises(ConventionsError) as exc:
        Conventions(alpha_doc)
    assert "headers.ruling" in str(exc.value)


def test_the_named_ruling_header_refusal_is_reached_only_by_a_non_list_falsy(
        alpha_doc):
    """MEASURED. `headers.ruling` is outside MAY_BE_EMPTY, so `[]` is caught by
    the generic empty check and the named message below it never fires for the
    case it was written for. It IS reachable, by a falsy value the generic
    check's membership test does not recognise - which is what this pins, so
    that neither branch is silently lost."""
    _set(alpha_doc, "headers.ruling", 0)
    with pytest.raises(ConventionsError) as exc:
        Conventions(alpha_doc)
    assert "headers.ruling is empty" in str(exc.value)
    assert "declaration error rather than an empty table" in str(exc.value)


# ---------------------------------------------------------------------------
# MEASURED: which required fields refuse an empty declaration
# ---------------------------------------------------------------------------

def test_the_set_of_fields_that_refuse_emptiness_is_the_one_measured():
    """A CENSUS, not a judgement. `MAY_BE_EMPTY` decides which fields a repo may
    declare empty; every required field outside it must be given a value even
    when the repo's honest answer is `none`. The list is pinned so that a change
    to it is visible in a diff rather than discovered by a repo that cannot
    describe itself.

    Measured 2026-08-11 against record_index 0.1.0.
    """
    must_be_filled = sorted(set(REQUIRED_FIELDS) - MAY_BE_EMPTY)
    assert must_be_filled == [
        "corpora.experiments_dir",
        "corpora.law_files",
        "corpora.record_roots",
        "corpora.record_top_files",
        "discovery.experiment_file",
        "discovery.experiment_prefix",
        "discovery.kickoff_arc",
        "discovery.kickoff_doc",
        "discovery.report_file_fragment",
        "discovery.ruling_arc",
        "discovery.ruling_doc",
        "headers.handoff",
        "headers.ruling",
        "headers.sub_closure",
        "headers.sub_ruling",
        "markers",
        "repo.db_env",
        "repo.db_rel",
        "repo.name",
        "sweep.banner",
        "sweep.claim_families",
        "sweep.current_state_dirs",
        "sweep.current_state_files",
        "sweep.historical_dirs",
        "vocabularies.artifact_extensions",
        "vocabularies.artifact_kinds",
        "vocabularies.authority",
        "vocabularies.experiment_status",
        "vocabularies.status_words",
        "vocabularies.supersede_verbs",
        "vocabularies.verdicts",
    ]


@pytest.mark.xfail(strict=True, reason=(
    "FINDING. conventions.py's own law is that declaring a corpus empty is a "
    "statement where omitting the key is not - and MAY_BE_EMPTY grants that to "
    "prose_files, profile_files and eight others. It does NOT grant it to "
    "sweep.current_state_dirs, sweep.historical_dirs, headers.handoff or "
    "vocabularies.supersede_verbs, so a repo whose honest answer is `none` for "
    "any of those cannot say so: the loader refuses `[]` and the repo must "
    "instead declare a value that matches nothing. Both fixture repos here "
    "carry a directory they would otherwise not have, for this reason."))
def test_a_repo_with_no_current_state_directory_can_declare_that(alpha_doc):
    _set(alpha_doc, "sweep.current_state_dirs", [])
    Conventions(alpha_doc)


# ---------------------------------------------------------------------------
# the arc rules
# ---------------------------------------------------------------------------

def test_alphas_ruling_arc_strips_from_the_keyword(alpha_conv):
    assert alpha_conv.arc_of_ruling_doc("E01-ruling.md") == "E01"
    assert alpha_conv.arc_of_ruling_doc("E02-ruling.md") == "E02"
    assert alpha_conv.arc_of_ruling_doc("E02-offsurface-ruling.md") == "E02-offsurface"


def test_betas_ruling_arc_takes_the_leading_token(beta_conv):
    assert beta_conv.arc_of_ruling_doc("A01-decision.md") == "A01"
    assert beta_conv.arc_of_ruling_doc("A02-decision.md") == "A02"


def test_the_two_arc_rules_disagree_on_the_same_filename(alpha_conv, beta_conv):
    """The same input, two declared rules, two answers - which is the property
    that makes the rule a declaration rather than a default."""
    fn = "E02-offsurface-ruling.md"
    assert alpha_conv.arc_of_ruling_doc(fn) == "E02-offsurface"
    assert beta_conv.arc_of_ruling_doc(fn) == "E02"


def test_the_kickoff_rule_is_deliberately_the_other_one(alpha_conv, beta_conv):
    """The asymmetry between a repo's two arc rules is real and declared. alpha
    strips a ruling document and takes the leading token of a kickoff; beta does
    the reverse."""
    assert alpha_conv.arc_of_kickoff_doc("E01-executor-kickoff.md") == "E01"
    assert beta_conv.arc_of_kickoff_doc("A01-executor-brief.md") == "A01-executor"


def test_an_arc_rule_naming_no_known_form_refuses(alpha_doc):
    _set(alpha_doc, "discovery.ruling_arc", {"invented": True})
    conv = Conventions(alpha_doc)
    with pytest.raises(ConventionsError) as exc:
        conv.arc_of_ruling_doc("E01-ruling.md")
    assert "no known rule" in str(exc.value)


def test_the_experiment_key_is_the_prefix_and_is_none_when_absent(alpha_conv):
    """`experiment` is GROUPING, a non-key column, and it says None rather than
    guessing when a filename carries no prefix."""
    assert alpha_conv.experiment_of("E02-offsurface-ruling.md") == "E02"
    assert alpha_conv.experiment_of("E02-ruling.md") == "E02"
    assert alpha_conv.experiment_of("INDEX.md") is None


# ---------------------------------------------------------------------------
# the seeded shape is preserved, not normalised
# ---------------------------------------------------------------------------

def test_a_bare_seeded_target_stays_a_bare_pair(alpha_conv):
    """Callers unpack the bare form directly - `_, _, (f, a) = SEEDED[0]` - so
    wrapping every target in a list to make one loop tidier is a change to a
    public surface."""
    question, phrase, target = alpha_conv.seeded[0]
    assert isinstance(target, tuple) and len(target) == 2
    want_file, want_anchor = target
    assert want_file == "docs/experiments/E01-ruling.md"
    assert want_anchor == "Ruling 1a"


def test_a_multi_target_seed_stays_a_list_of_pairs(alpha_doc):
    alpha_doc["verify"]["seeded"] = [
        ["two targets", "a phrase", [["CLAUDE.md", None], ["OVERVIEW.md", None]]]]
    conv = Conventions(alpha_doc)
    _, _, target = conv.seeded[0]
    assert isinstance(target, list) and len(target) == 2
    assert target[0] == ("CLAUDE.md", None)


def test_a_seeded_target_that_is_not_a_pair_refuses_and_names_the_question(
        alpha_doc):
    alpha_doc["verify"]["seeded"] = [
        ["the malformed one", "a phrase", ["only-a-file.md"]]]
    with pytest.raises(ConventionsError) as exc:
        Conventions(alpha_doc)
    assert "(file, anchor)" in str(exc.value)
    assert "the malformed one" in str(exc.value)


# ---------------------------------------------------------------------------
# load() itself
# ---------------------------------------------------------------------------

def test_a_missing_declaration_refuses_and_names_the_path(tmp_path):
    missing = str(tmp_path / "nowhere" / "conventions.json")
    with pytest.raises(ConventionsError) as exc:
        load(missing)
    assert missing in str(exc.value)
    assert "supplies no default" in str(exc.value)


def test_unreadable_json_refuses_as_a_conventions_error_not_a_valueerror(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(ConventionsError) as exc:
        load(str(p))
    assert "not readable JSON" in str(exc.value)


def test_the_source_path_is_carried_for_the_error_message(alpha_conv):
    assert alpha_conv.source.endswith("conventions.json")


# ---------------------------------------------------------------------------
# the declaration survives a round trip through its own doc
# ---------------------------------------------------------------------------

def test_the_underscore_prefixed_notes_are_ignored_by_the_loader(alpha_doc):
    """Both fixtures carry `_note` keys explaining their choices. They are prose
    for a reader and must not become fields."""
    assert any(k.startswith("_") for k in alpha_doc)
    conv = Conventions(copy.deepcopy(alpha_doc))
    assert not any(k.startswith("_") for k in vars(conv) if k != "_validate")
