"""Vocabularies that report what they did NOT recognise.

⚑ THE LAW THIS FILE EXISTS FOR (S02 step-2 ruling, Ruling 3):

    A missing file raises; a non-matching vocabulary returns nothing and says
    nothing.

Measured, not supposed. Running facet's parsers against a second record found
three LOUD failures - a missing file raises FileNotFoundError and stops the
build - and two SILENT ones that nobody had predicted:

  * the law corpus parsed 38 rows and left `paid_for_by` NULL on every one,
    because the declared pattern matched an arc range that repo does not use;
  * six artifact mentions were dropped - `.mp4` x3 and `.mkv` x3, in the repo
    whose entire product is video - because the extension map had no video
    entry.

An empty table and a table that silently discarded six artifacts are
indistinguishable at the call site, and only one of them is correct.

⚑ AND THE COUNTER HAS TO BE ABLE TO MOVE. This repo's law: *grade an arm only
on what it can move - ask what the metric reads when the arm does nothing and
when it works perfectly; if those are the same number it is not measuring the
arm.* Counting "every ruling that named no phenomenon" would read in the
hundreds on a healthy record and mean nothing.

So every vocabulary declares a PROBE: a pattern describing what an input of its
kind looks like. The probe defines the population; `unrecognised` counts inputs
inside that population which matched no entry. On a record whose vocabulary is
complete that count is 0, and on the video record above it is 6 with `.mp4` and
`.mkv` named. Those are different numbers, so the counter measures something.

REPORT, NOT GATE. `verify` surfaces these counts and does not fail on them - a
diagnostic and a gate are different objects, and which unrecognised inputs
matter is a judgement about a record, not a property of one. Whether any of
these should gate is named as an open question in the extraction's report
rather than decided here.
"""
import re


class Vocabulary(object):
    """A named set of recognised inputs, plus a count of the ones it missed.

    `probe` is what makes the miss count meaningful: without it every input the
    record contains is a candidate and the number is noise.
    """

    def __init__(self, name, probe=None, samples=8):
        self.name = name
        self.probe = re.compile(probe) if isinstance(probe, str) else probe
        self.recognised = 0
        self.unrecognised = 0
        self._samples = {}
        self._sample_cap = samples

    def _note(self, token, where):
        self.unrecognised += 1
        key = str(token)
        if key not in self._samples and len(self._samples) < self._sample_cap:
            self._samples[key] = where

    def in_population(self, text):
        """Whether this input is one this vocabulary is responsible for."""
        return True if self.probe is None else bool(self.probe.search(text))

    def hit(self):
        self.recognised += 1

    def miss(self, token, where=None):
        self._note(token, where)

    @property
    def samples(self):
        return sorted(self._samples.items())

    @property
    def total(self):
        return self.recognised + self.unrecognised

    def line(self):
        """One transcript row. Named tokens, because a count nobody can act on
        is a count everybody learns to ignore."""
        head = ("  %-22s recognised %5d   unrecognised %4d"
                % (self.name, self.recognised, self.unrecognised))
        if not self.unrecognised:
            return head
        named = ", ".join(t for t, _ in self.samples)
        # DISTINCT tokens are capped for legibility; the COUNT above is always
        # exact. A truncated list that did not say it was truncated would be
        # the same silent-drop defect one layer up.
        extra = ("" if len(self._samples) >= self.unrecognised
                 else "  (+%d more occurrence(s))"
                      % (self.unrecognised - len(self._samples)))
        return head + "\n      not recognised: %s%s" % (named, extra)


class VocabReport(object):
    """Every vocabulary of one build, collected so verify can print them.

    Built fresh per build rather than at module level. facet's own index had a
    module-level accumulator that was appended to and never cleared, and
    `verify` calls `build` three times in one process - so a per-build object is
    the shape, not a convenience.
    """

    def __init__(self):
        self._v = {}

    def get(self, name, probe=None):
        if name not in self._v:
            self._v[name] = Vocabulary(name, probe=probe)
        return self._v[name]

    def __iter__(self):
        for k in sorted(self._v):
            yield self._v[k]

    @property
    def total_unrecognised(self):
        return sum(v.unrecognised for v in self)

    def render(self):
        """The transcript block. Printed BEFORE verify's verdict line, because
        the last non-empty line of a verify transcript is its verdict and that
        is a contract other tools read."""
        out = ["[vocabulary] what each declared vocabulary did not recognise",
               "             REPORT ONLY - this section never fails the run"]
        for v in self:
            out.append(v.line())
        if not self._v:
            out.append("  (no vocabulary was exercised by this build)")
        out.append("  total unrecognised inputs: %d" % self.total_unrecognised)
        return "\n".join(out)


# ---------------------------------------------------------------------------
# the probes - what an input of each kind LOOKS like
# ---------------------------------------------------------------------------
#
# Each is deliberately broader than its vocabulary and narrower than the corpus.
# Too narrow and the counter can never fire; too broad and it fires on prose.

#: ⚑ THE ANNOUNCING FORM, not "any capitalised word". The first draft of this
#: probe was `\b[A-Z]{4,}\b` and its first run against a real record reported 824
#: unrecognised "verdicts" - ADJUDICATED, BASELINE, OWNER, PASS, SEAM, WHITE -
#: which are capitalised words in prose and not verdicts at all. A counter that
#: cries wolf 824 times is a counter every reader learns to skip, and this file's
#: own premise is that a warning nobody can act on is a warning nobody reads.
#:
#: The population is a holding that ANNOUNCES: `the pair IS ACCEPTED`, `is
#: RATIFIED end to end`. That is the shape a verdict actually takes here, so a
#: shouted verb the vocabulary does not claim is a real miss and an ordinary
#: capitalised noun is not in the population at all.
#: ⚑ AND THE SHOUTED WORD IS A PAST PARTICIPLE. Narrowed ONCE more, on a stated
#: morphological rule rather than by tuning toward a nicer number: a verdict is
#: something DONE to a thing - ACCEPTED, RATIFIED, WITHDRAWN, MINTED, BANKED -
#: so it is announced as a participle. `is NOT`, `is NOW`, `is NONE`, `is WHITE`
#: match the announcing form and are not verdicts, and excluding them
#: STRUCTURALLY beats a stoplist that would grow forever.
#:
#: The boundary this buys is stated rather than hidden: a declared verdict that
#: is not a participle - facet declares `VOID` - is outside the population, so
#: its holdings are neither hit nor miss. That is a known blind spot of the
#: COUNTER, not of the parser: `VOID` still classifies exactly as before.
PROBE_ANNOUNCED = r"\b(?:is|IS|are|ARE|was|WAS)\s+([A-Z]{3,}(?:ED|EN))\b"

#: phenomena share the announcing form, so their population is the RESIDUAL: a
#: shouted announcement that the verdict vocabulary did not already claim.
#: Without the subtraction every `is ACCEPTED` would be counted as a phenomenon
#: this tool failed to recognise, which is false - it is a verdict, recognised by
#: the vocabulary next door.
PROBE_PHENOMENON = PROBE_ANNOUNCED

#: kept under its old name for callers; same value.
PROBE_VERDICT = PROBE_ANNOUNCED

#: a path-shaped token with an extension. The population for artifact kinds is
#: every such token, so an extension the map does not carry is countable.
PROBE_ARTIFACT = r"\.[A-Za-z0-9]{1,6}$"

#: a `##` heading opening with something numbered - the population the ruling
#: header patterns are responsible for. This is the probe that would have caught
#: `## N. RULING -` on the first run against a second record.
PROBE_RULING_HEADER = r"^#{2,3} +(?:Ruling\b|\d+\.)"
