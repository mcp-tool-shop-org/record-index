"""mechanism.py - tuning, with the corpus it was fit to named at the site.

THE COUNTERPART TO conventions.py, and the axis is the whole design: a repo must
declare what its documents MEAN and may inherit how the search is TUNED. So the
checks here are about the boundary - that an override which is really a
convention is refused, and that every default carries the corpus and date it was
calibrated on rather than shipping bare.
"""
import pytest

from record_index.mechanism import DEFAULT, Mechanism


def test_the_default_is_a_mechanism_with_the_class_values():
    assert isinstance(DEFAULT, Mechanism)
    assert DEFAULT.BM25_TITLE_WEIGHT == Mechanism.BM25_TITLE_WEIGHT
    assert DEFAULT.CANDIDATES == Mechanism.CANDIDATES


def test_an_override_replaces_one_value_and_leaves_the_rest():
    m = Mechanism(PHRASE_SLOTS=1)
    assert m.PHRASE_SLOTS == 1
    assert m.CANDIDATES == Mechanism.CANDIDATES
    assert DEFAULT.PHRASE_SLOTS == Mechanism.PHRASE_SLOTS, (
        "an override mutated the class and so leaked into every other caller")


def test_an_unknown_override_refuses_and_says_where_the_value_belongs():
    """Anything about what a document MEANS is a convention and belongs in the
    declaration. A silent `setattr` here is how a convention ends up living in
    the tuning object, which is the axis this split exists to hold."""
    with pytest.raises(ValueError) as exc:
        Mechanism(RULING_HEADER="^## Ruling")
    assert "RULING_HEADER" in str(exc.value)
    assert "belongs in the declaration" in str(exc.value)


def test_a_lower_case_name_is_refused_even_when_the_attribute_exists():
    """`calibration_note` is a method on this class. Accepting it as an override
    would let a caller replace behaviour through a tuning constructor."""
    with pytest.raises(ValueError) as exc:
        Mechanism(calibration_note="not a tuning value")
    assert "calibration_note" in str(exc.value)


def test_several_unknown_overrides_are_all_named_not_just_the_first():
    with pytest.raises(ValueError) as exc:
        Mechanism(ZED=1, ABLE=2)
    assert "ABLE" in str(exc.value) and "ZED" in str(exc.value)


def test_the_calibration_note_carries_the_corpus_and_the_numbers_it_quotes():
    """SHIPPING A DEFAULT BARE HIDES THAT IT WAS FIT TO ONE CORPUS. A reader who
    wants to know whether 400 means anything for their record can see that it
    does not yet."""
    note = DEFAULT.calibration_note()
    assert "facet@2026-08" in note
    assert "defaults, not measurements about your record" in note
    assert str(DEFAULT.CANDIDATES) in note
    assert str(DEFAULT.PHRASE_SLOTS) in note


def test_an_overridden_mechanism_reports_its_own_values_in_the_note():
    """The note must follow the object, or a report would quote a number the run
    did not use."""
    note = Mechanism(CANDIDATES=25, PHRASE_SLOTS=1).calibration_note()
    assert "candidates 25" in note
    assert "phrase slots 1" in note


@pytest.mark.parametrize("name", [
    "BM25_TITLE_WEIGHT", "BM25_BODY_WEIGHT", "CANDIDATES", "PHRASE_SLOTS",
    "ONE_LINE_LIMIT", "MIN_LAW_STATEMENT", "MIN_PROSE_BODY",
    "SUPERSEDE_BODY_SCAN", "ARTIFACT_BODY_CAP", "PHENOMENON_BODY_CAP",
    "STALE_NAMES", "GET_DEFAULT_LINES", "GET_MAX_LINES", "TRANSCRIPT_TAIL"])
def test_every_tuning_value_is_overridable(name):
    """A value that could not be overridden would be a convention hiding in the
    mechanism half."""
    m = Mechanism(**{name: 7})
    assert getattr(m, name) == 7


def test_the_title_weight_outranks_the_body_weight():
    """Not a tuning preference - the ranking design. Titles are the search
    surface and bodies are context, and a build where these were equal would
    silently change what every seeded question returns."""
    assert DEFAULT.BM25_TITLE_WEIGHT > DEFAULT.BM25_BODY_WEIGHT
