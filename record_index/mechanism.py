"""HOW the search works. Defaults with overrides, each naming its calibration.

The counterpart to conventions.py. A repo declares what its documents MEAN and
inherits how the search is TUNED, because nobody adopting this tool has evidence
to tune BM25 with, and inviting them to turn knobs they cannot evaluate is worse
than a default (S02 step-2 ruling, answer 1).

⚑ BUT SHIPPING THEM BARE HIDES THAT THEY WERE FIT TO ONE CORPUS. Every value
below carries the corpus and date it was calibrated on, at the site. That is the
whole difference between a default and a number somebody once measured
somewhere: a reader who wants to know whether 400 means anything for their
record can see that it does not yet.

None of these is a convention. A repo that overrides one is tuning, not
declaring, and the override does not change what any document MEANS.
"""


class Mechanism(object):
    """Tuning values. Constructed with defaults; a repo may override any of them.

    CALIBRATION, ONE LINE PER VALUE. `facet@2026-08` means: measured on the facet
    record as it stood in August 2026 - roughly 250 markdown files, 62k lines,
    one house style. It is NOT a claim that the value transfers.
    """

    #: bm25 column weights (title, body). Falsified alternatives are recorded in
    #: query()'s docstring: coordination-level as primary sort scored 9/14 and
    #: title-coverage-first 11/14, against 13/14 for scaling. Every variant is a
    #: generic retrieval mechanism; none knows about a specific document.
    #: CALIBRATED: facet@2026-08, seeded set of 19.
    BM25_TITLE_WEIGHT = 8.0
    BM25_BODY_WEIGHT = 1.0

    #: re-ranking window; fixed rather than derived, so `q` is deterministic.
    #: CALIBRATED: facet@2026-08 - large enough that the seeded targets were
    #: inside it, never tuned against a target that was outside.
    CANDIDATES = 400

    #: exact-phrase hits are a BEST-BET SLOT, not a takeover. Uncapped, a phrase
    #: appearing in a pointer document monopolises the page.
    #: CALIBRATED: facet@2026-08 - measured on a record whose own dispatch quotes
    #: every seeded question verbatim, which is what made the cap necessary.
    PHRASE_SLOTS = 3

    #: a holding longer than this is truncated with an ellipsis.
    #: CALIBRATED: facet@2026-08, chosen to fit a terminal row; no measurement
    #: behind the exact figure, and it is named here rather than left unnamed.
    ONE_LINE_LIMIT = 240

    #: a law statement shorter than this is not a law - it is a fragment of one.
    #: CALIBRATED: facet@2026-08 on CLAUDE.md's bold-lead corpus.
    MIN_LAW_STATEMENT = 12

    #: a prose section shorter than this is not indexed on its own.
    #: CALIBRATED: facet@2026-08.
    MIN_PROSE_BODY = 40

    #: how much of a row's body the supersession linker reads.
    #: CALIBRATED: facet@2026-08 - long enough to reach the correction verbs in
    #: the longest ruling measured then.
    SUPERSEDE_BODY_SCAN = 4000

    #: caps on accumulated artifact / phenomenon body text.
    #: CALIBRATED: facet@2026-08.
    ARTIFACT_BODY_CAP = 1200
    PHENOMENON_BODY_CAP = 4000

    #: how many named files per class a staleness banner lists before "and N more".
    STALE_NAMES = 12

    #: record_get's default and maximum block sizes.
    GET_DEFAULT_LINES = 120
    GET_MAX_LINES = 400

    #: how many transcript lines a write verb echoes; the full transcript is in
    #: the certificate, so this is a convenience, not the record.
    TRANSCRIPT_TAIL = 15

    def __init__(self, **overrides):
        unknown = [k for k in overrides
                   if not (k.isupper() and hasattr(Mechanism, k))]
        if unknown:
            raise ValueError(
                "unknown mechanism override(s): %s. Mechanism carries tuning "
                "only; anything about what a document MEANS is a convention and "
                "belongs in the declaration." % ", ".join(sorted(unknown)))
        for k, v in overrides.items():
            setattr(self, k, v)

    def calibration_note(self):
        """One line a report can print so a quoted number carries its provenance."""
        return ("mechanism: bm25(%.1f, %.1f), candidates %d, phrase slots %d "
                "- calibrated on facet@2026-08 (~250 files / 62k lines, seeded "
                "set 19); these are defaults, not measurements about your record"
                % (self.BM25_TITLE_WEIGHT, self.BM25_BODY_WEIGHT,
                   self.CANDIDATES, self.PHRASE_SLOTS))


DEFAULT = Mechanism()
