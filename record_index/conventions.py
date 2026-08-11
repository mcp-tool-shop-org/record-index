"""What a record repo DECLARES about its own documents.

CONVENTIONS ARE A FULL DECLARATION, NOT OVERRIDES (S02 step-2 ruling, answer 4).
There is deliberately no "if the repo did not say, use facet's value" branch in
this file. An overrides model ships one repo's history as every other repo's
silent default, and a second repo then inherits a first repo's past by omission
- which is the exact defect the extraction was halted to fix. So: every field
below is required, absence is an error that names the field, and the error is
raised at load time rather than surfacing as an empty table six steps later.

MECHANISM IS THE OPPOSITE and lives in mechanism.py: defaults with overrides,
each carrying the corpus and date it was calibrated on. You must declare what
your repo MEANS; you may inherit how the search is TUNED.

WHAT LIVES HERE THAT USED TO LIVE IN A FUNCTION BODY. Twelve facet-specific
sites carried no constant name at all - nine hardcoded arc bounds inside
verify(), an experiment span, a list of facet's own filename fragments, a
`startswith("E15-")` self-reference exclusion - and a parameterisation that
moved only the named constants would have carried every one of them into this
package invisibly. They are declared fields now. The list of what moved is in
docs/lifted-sites.md, keyed to the line it came from.

ARC vs EXPERIMENT (S02 step-3 ruling, Ruling 3). `arc` is IDENTITY - it is part
of `rulings`' primary key, and `E10` and `E10-offsurface` are two ruling series
that both number from 1, so collapsing them collides on seven keys. `experiment`
is GROUPING - the `E\\d\\d` prefix, a non-key column, so "every ruling for E02"
is one WHERE clause. The schema says both rather than picking one.
"""
import io
import json
import os
import re


CONVENTIONS_SCHEMA = "record-index-conventions/1"

# Every declared field, as a dotted path. A repo's file must carry all of them.
# Written as an explicit list rather than derived from a sample declaration,
# because a schema derived from one repo's file is that repo's file wearing a
# schema's clothes.
REQUIRED_FIELDS = (
    "repo.name", "repo.db_rel", "repo.db_env",
    "markers",
    "corpora.experiments_dir", "corpora.record_roots", "corpora.record_top_files",
    "corpora.law_files", "corpora.prose_files", "corpora.profile_files",
    "corpora.experiments_table", "corpora.sweep_extra_files",
    "corpora.sweep_extra_dirs",
    "discovery.ruling_doc", "discovery.kickoff_doc", "discovery.ruling_arc",
    "discovery.kickoff_arc", "discovery.experiment_prefix",
    "discovery.experiment_file", "discovery.spec_file_fragments",
    "discovery.report_file_fragment", "discovery.topical_ruling_files",
    "headers.ruling", "headers.addenda", "headers.amendment", "headers.handoff",
    "headers.sub_ruling", "headers.sub_closure",
    "vocabularies.verdicts", "vocabularies.authority",
    "vocabularies.experiment_status", "vocabularies.status_words",
    "vocabularies.artifact_kinds", "vocabularies.artifact_extensions",
    "vocabularies.phenomenon_markers", "vocabularies.supersede_verbs",
    "laws.paid_for_by",
    "sweep.current_state_files", "sweep.current_state_dirs",
    "sweep.historical_dirs", "sweep.bannered", "sweep.banner",
    "sweep.split_at_release", "sweep.current_state_extra",
    "sweep.historical_extra", "sweep.self_reference_exclude",
    "sweep.claim_families",
    "verify.count_checks", "verify.sequences", "verify.handoff_coverage",
    "verify.experiment_coverage", "verify.seeded",
)

# Fields that may be declared EMPTY but must still be declared. Being explicit
# about "this repo has no profiles registry" is a different statement from
# leaving the key out, and only one of them is a declaration.
MAY_BE_EMPTY = frozenset((
    "corpora.prose_files", "corpora.profile_files", "corpora.sweep_extra_files",
    "corpora.sweep_extra_dirs", "corpora.experiments_table",
    "discovery.topical_ruling_files", "discovery.spec_file_fragments",
    "laws.paid_for_by", "sweep.current_state_extra", "sweep.historical_extra",
    "sweep.self_reference_exclude", "sweep.bannered", "sweep.split_at_release",
    "verify.count_checks", "verify.sequences", "verify.handoff_coverage",
    "verify.experiment_coverage", "verify.seeded", "vocabularies.phenomenon_markers",
    "headers.addenda", "headers.amendment",
))


class ConventionsError(Exception):
    """A repo's declaration is missing, unreadable, or incomplete.

    Raised at LOAD time and naming the field, because the alternative is what
    the extraction measured: a declaration gap surfacing as an empty table at a
    call site with nothing to point at.
    """


def _dig(doc, path):
    cur = doc
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


class Conventions(object):
    """One repo's declaration, validated, with its patterns compiled once."""

    def __init__(self, doc, source=None):
        self.doc = doc
        self.source = source
        self._validate()
        d = doc

        self.name = d["repo"]["name"]
        self.db_rel = d["repo"]["db_rel"]
        self.db_env = d["repo"]["db_env"]
        self.markers = tuple(d["markers"])

        c = d["corpora"]
        self.experiments_dir = c["experiments_dir"]
        self.record_roots = list(c["record_roots"])
        self.record_top_files = list(c["record_top_files"])
        self.law_files = list(c["law_files"])
        self.prose_files = list(c["prose_files"])
        self.profile_files = list(c["profile_files"])
        self.experiments_table = c["experiments_table"] or None
        self.sweep_extra_files = list(c["sweep_extra_files"])
        self.sweep_extra_dirs = list(c["sweep_extra_dirs"])

        v = d["discovery"]
        self.ruling_doc_re = re.compile(v["ruling_doc"])
        self.kickoff_doc_re = re.compile(v["kickoff_doc"])
        self.ruling_arc = v["ruling_arc"]
        self.kickoff_arc = v["kickoff_arc"]
        self.experiment_prefix_re = re.compile(v["experiment_prefix"])
        self.experiment_file_re = re.compile(v["experiment_file"])
        self.spec_file_fragments = list(v["spec_file_fragments"])
        self.report_file_fragment = v["report_file_fragment"]
        self.topical_ruling_files = [tuple(x) for x in v["topical_ruling_files"]]

        h = d["headers"]
        # ⚑ A LIST, not a pattern (S02 step-2 ruling, answer 3). A shared tool
        # that hard-codes one ruling-header form breaks on the third repo as
        # surely as on the second, and the convention is plural in practice:
        # armature's early ruling documents write `## N. RULING -` and its
        # closing ones write `## Ruling N`.
        self.ruling_hdrs = [re.compile(p) for p in h["ruling"]]
        self.addenda_hdrs = [re.compile(p) for p in h["addenda"]]
        self.amendment_hdrs = [re.compile(p) for p in h["amendment"]]
        self.handoff_hdrs = [re.compile(p) for p in h["handoff"]]
        self.sub_ruling_re = re.compile(h["sub_ruling"])
        self.sub_closure_re = re.compile(h["sub_closure"])

        b = d["vocabularies"]
        self.verdicts = list(b["verdicts"])
        self.authority_re = re.compile(b["authority"]["pattern"])
        self.authority_named = b["authority"]["named"]
        self.authority_default = b["authority"]["default"]
        self.experiment_status = list(b["experiment_status"])
        self.status_words = [tuple(x) for x in b["status_words"]]
        self.artifact_kinds = dict(b["artifact_kinds"])
        self.artifact_extensions = list(b["artifact_extensions"])
        self.phenomenon_markers = [tuple(x) for x in b["phenomenon_markers"]]
        self.supersede_verbs = list(b["supersede_verbs"])

        self.paid_for_by_re = (re.compile(d["laws"]["paid_for_by"])
                               if d["laws"]["paid_for_by"] else None)

        s = d["sweep"]
        self.current_state_files = set(s["current_state_files"])
        self.current_state_dirs = tuple(s["current_state_dirs"])
        self.historical_dirs = tuple(s["historical_dirs"])
        self.bannered = s["bannered"] or None
        self.banner_re = re.compile(s["banner"])
        self.split_at_release = s["split_at_release"] or None
        self.current_state_extra = dict(s["current_state_extra"])
        self.historical_extra = dict(s["historical_extra"])
        self.self_reference_exclude = tuple(s["self_reference_exclude"])
        self.claim_families = [
            (f["label"], f["kind"], f["unit"], re.compile(f["pattern"]))
            for f in s["claim_families"]]

        y = d["verify"]
        self.count_checks = [tuple(x) for x in y["count_checks"]]
        self.sequences = [tuple(x) for x in y["sequences"]]
        self.handoff_coverage = y["handoff_coverage"] or None
        self.experiment_coverage = y["experiment_coverage"] or None
        # ⚑ THE SHAPE IS PRESERVED, NOT NORMALISED. A seeded row is
        # (question, phrase, target) where `target` is a BARE (file, anchor)
        # tuple for the ordinary one-target case and a LIST of them where a
        # question legitimately has several. Callers unpack the bare form
        # directly - `_, _, (want_file, want_anchor) = SEEDED[0]` - so wrapping
        # every target in a list to make one loop tidier is a change to a public
        # surface, and it broke three tests that had bound to the original shape
        # before this comment was written. Normalising happens where the loop
        # is, not here.
        self.seeded = []
        for r in y["seeded"]:
            tgt = r[2]
            multi = bool(tgt) and isinstance(tgt[0], (list, tuple))
            value = [tuple(t) for t in tgt] if multi else tuple(tgt)
            for p in (value if multi else [value]):
                if len(p) != 2:
                    raise ConventionsError(
                        "a seeded target is (file, anchor); got %r in row %r"
                        % (p, r[0]))
            self.seeded.append((r[0], r[1], value))

    # -- validation ---------------------------------------------------------

    def _validate(self):
        d = self.doc
        if not isinstance(d, dict):
            raise ConventionsError(
                "a conventions declaration is a JSON object; got %s"
                % type(d).__name__)
        got = d.get("schema")
        if got != CONVENTIONS_SCHEMA:
            raise ConventionsError(
                "conventions schema is %r, this tool reads %r%s"
                % (got, CONVENTIONS_SCHEMA,
                   " (%s)" % self.source if self.source else ""))
        missing = []
        empty = []
        for path in REQUIRED_FIELDS:
            val, present = _dig(d, path)
            if not present:
                missing.append(path)
            elif val in ((), [], {}, "", None) and path not in MAY_BE_EMPTY:
                empty.append(path)
        if missing:
            raise ConventionsError(
                "the declaration is incomplete - %d field(s) not declared: %s. "
                "Conventions are a FULL declaration: there is no default for a "
                "field you did not state, because the default would be another "
                "repo's history." % (len(missing), ", ".join(sorted(missing))))
        if empty:
            raise ConventionsError(
                "declared but empty, and these may not be empty: %s"
                % ", ".join(sorted(empty)))
        if not d["headers"]["ruling"]:
            raise ConventionsError(
                "headers.ruling is empty - a record with no ruling-header form "
                "declared can carry no rulings, which is a declaration error "
                "rather than an empty table")

    # -- the derivations that used to be inline -----------------------------

    def arc_of_ruling_doc(self, filename):
        """The arc label - IDENTITY, part of the rulings primary key.

        ⚑ Stem-derived, and that is load-bearing rather than stylistic (S02
        step-3 ruling, Ruling 3). Measured before it was ruled: keyed on the
        E-number alone, facet's `E10-ruling.md` (rulings 1-12) and
        `E10-offsurface-ruling.md` (rulings 1-7) both become arc `E10` and
        collide on SEVEN primary keys, and build() raises IntegrityError. The
        grouping that made the prefix attractive is served by `experiment`
        below, which costs nothing because it is not part of any key.
        """
        rule = self.ruling_arc
        if "strip_from" in rule:
            return re.split(r"-?" + rule["strip_from"], filename,
                            maxsplit=1)[0].rstrip("-")
        if rule.get("leading"):
            return filename.split("-", 1)[0]
        raise ConventionsError("discovery.ruling_arc declares no known rule: %r"
                               % (rule,))

    def arc_of_kickoff_doc(self, filename):
        """Deliberately a DIFFERENT rule from the ruling one, and declared as
        such rather than hidden in a function body.

        Stripping from the keyword here would yield `E04-executor` and
        `E15-context-index` - labels the handoffs table has never used, which
        would break every existing anchor. The asymmetry is real; making it two
        declared fields is what stops it being a surprise.
        """
        rule = self.kickoff_arc
        if rule.get("leading"):
            return filename.split("-", 1)[0]
        if "strip_from" in rule:
            return re.split(r"-?" + rule["strip_from"], filename,
                            maxsplit=1)[0].rstrip("-")
        raise ConventionsError("discovery.kickoff_arc declares no known rule: %r"
                               % (rule,))

    def experiment_of(self, filename):
        """The GROUPING key - the `E\\d\\d` prefix, a non-key column.

        None when the filename carries no prefix, which is reported rather than
        guessed at.
        """
        m = self.experiment_prefix_re.match(filename)
        return m.group(1) if m else None


def load(path):
    """Read and validate one repo's declaration."""
    if not os.path.exists(path):
        raise ConventionsError(
            "no conventions declaration at %s. A record repo declares what its "
            "documents mean; this tool supplies no default for that." % path)
    with io.open(path, encoding="utf-8") as fh:
        try:
            doc = json.load(fh)
        except ValueError as exc:
            raise ConventionsError("%s is not readable JSON: %s" % (path, exc))
    return Conventions(doc, source=path)
