"""record-index - a governed SQLite+FTS5 map over a markdown decision record.

WHAT A CONSUMING REPO DOES. It ships a conventions declaration and a four-line
adapter:

    import record_index
    B = record_index.bind(__file__)          # finds the record root and the
    globals().update(B.exports())            # declaration, binds both

`bind` resolves the record root BY TESTING FOR IT, never by assuming: the
markers a repo declares are looked for in the module's parent directory and then
in the working directory. A resolver that cannot find a corpus REFUSES and
returns None rather than a plausible-looking directory - a fallback there only
moves the failure one caller downstream.
"""
import os

from .conventions import Conventions, ConventionsError, load  # noqa: F401
from .mechanism import DEFAULT, Mechanism                      # noqa: F401
from .parse import Record                                      # noqa: F401
from . import claims as _claims
from . import index as _index
from . import text as _text

__version__ = "0.1.0"

CONVENTIONS_REL = "docs/index/conventions.json"

EXIT_OK = _index.EXIT_OK
EXIT_USER = _index.EXIT_USER
EXIT_RUNTIME = _index.EXIT_RUNTIME
EXIT_PARTIAL = _index.EXIT_PARTIAL
EXIT_REFUSED = _index.EXIT_REFUSED


class RootNotFound(Exception):
    """No candidate directory contained the record. A refusal, not a defect."""


def is_record_root(path, markers):
    """Does this directory contain the record. The property, not a proxy.

    TWO markers, not one, and the second is not decoration: `CLAUDE.md` alone is
    an ordinary filename and many directories carry one. A single-marker
    resolver would bind a working directory that is some other repo entirely and
    then fail deeper in.
    """
    if not path:
        return False
    return all(os.path.exists(os.path.join(path, m.replace("/", os.sep)))
               for m in markers)


def resolve_root(here, markers, candidates=None):
    """The first candidate that contains the record, or None.

    The declared search order, most specific first: the directory this module's
    parent sits in (a source checkout), then the working directory (which is
    where an INSTALLED command is run from). There is deliberately no walk UP
    from cwd - it would resolve a subdirectory of a checkout, and would also
    reach a parent that is a DIFFERENT record.
    """
    if candidates is None:
        candidates = (os.path.dirname(here), os.getcwd())
    for cand in candidates:
        if is_record_root(cand, markers):
            return os.path.abspath(cand)
    return None


class Binding(object):
    """One repo's root + declaration + tuning, and the verbs bound to them."""

    def __init__(self, root, conventions, mechanism=None):
        self._root = root
        self._root_provider = None
        self.conv = conventions
        self.mech = mechanism or DEFAULT

    @property
    def root(self):
        """The record root, READ THROUGH A PROVIDER on every access.

        ⚑ Not captured, and the reason is a real one that a first draft of this
        adapter got wrong. A consuming repo's suite points the corpus gate at an
        empty directory by monkeypatching the adapter module's `REPO` global; a
        Binding that captured the root at construction made that patch a no-op,
        so twelve resolver tests went green against a value they were no longer
        setting. Reading through the provider is what keeps the patch load-
        bearing - and a test that cannot change what it is testing is the
        check-that-cannot-fail family, one layer down.
        """
        if self._root_provider is not None:
            return self._root_provider()
        return self._root

    def set_root_provider(self, fn):
        """Bind the root to a callable - typically an adapter's module global."""
        self._root_provider = fn
        return self

    def record(self):
        """A FRESH Record per call.

        Deliberate: a Record carries this build's findings and vocabulary
        counters, and `verify` builds three times in one process. Reusing one
        would accumulate counts across builds - which is the module-level
        accumulator defect this extraction inherited and did not carry forward.
        """
        return Record(self.root, self.conv, self.mech)

    def build(self, db_path, quiet=False, rec=None):
        return _index.build(rec or self.record(), db_path, quiet=quiet)

    def verify(self, db_path, top_n=3):
        return _index.verify(self.record(), db_path, top_n=top_n)

    def claims(self, db_path):
        return _claims.claims(self.record(), db_path)

    def query(self, con, phrase, limit=8):
        return _index.query(con, phrase, limit=limit, mech=self.mech)

    def db_default(self):
        return os.path.join(self.root, self.conv.db_rel.replace("/", os.sep))

    def exports(self):
        """The module-level names a consuming adapter re-exports.

        Named explicitly rather than by `dir()` sweep: an adapter's surface is a
        contract other tools and tests bind to, and a surface derived from
        whatever happened to be public is not one.

        With no corpus bound this returns the COMMAND half only - exit codes,
        the db identity, the generic text mechanism - and none of the declared
        patterns, because there is no declaration to surface. `--help` and a
        `--db`-explicit `q` need exactly the first half.
        """
        conv = self.conv
        if self.root is None:
            return {
                "REPO": None, "CONV": conv, "MECH": self.mech, "BINDING": self,
                "DB_REL": conv.db_rel, "DB_ENV": conv.db_env,
                "RECORD_MARKERS": ("CLAUDE.md", "docs/experiments"),
                "EXIT_OK": EXIT_OK, "EXIT_USER": EXIT_USER,
                "EXIT_RUNTIME": EXIT_RUNTIME, "EXIT_PARTIAL": EXIT_PARTIAL,
                "EXIT_REFUSED": EXIT_REFUSED,
                "DASH": _text.DASH, "one_line": _text.one_line,
                "strip_md": _text.strip_md, "find_date": _text.find_date,
                "fts_terms": _text.fts_terms, "fts_or": _text.fts_or,
                "STOPWORDS": _text.STOPWORDS, "SCHEMA": _index.SCHEMA,
                "build": self.build, "verify": self.verify,
                "claims": self.claims, "query": self.query,
                "survivable_stdout": _index.survivable_stdout,
            }
        rec = self.record()
        return {
            # identity
            "REPO": self.root, "CONV": conv, "MECH": self.mech, "BINDING": self,
            "DB_REL": conv.db_rel, "DB_ENV": conv.db_env,
            "RECORD_MARKERS": conv.markers,
            # exit codes
            "EXIT_OK": EXIT_OK, "EXIT_USER": EXIT_USER,
            "EXIT_RUNTIME": EXIT_RUNTIME, "EXIT_PARTIAL": EXIT_PARTIAL,
            "EXIT_REFUSED": EXIT_REFUSED,
            # declared patterns, surfaced as module attributes so a repo's own
            # tests can assert against the conventions it declared
            "RULING_DOC_RE": conv.ruling_doc_re,
            "KICKOFF_DOC_RE": conv.kickoff_doc_re,
            "RULING_HDR": conv.ruling_hdrs[0],
            "RULING_HDRS": conv.ruling_hdrs,
            "ADDENDA_HDR": (conv.addenda_hdrs[0] if conv.addenda_hdrs else None),
            "AMEND_HDR": (conv.amendment_hdrs[0] if conv.amendment_hdrs else None),
            "HANDOFF_HDR": (conv.handoff_hdrs[0] if conv.handoff_hdrs else None),
            "SUB_RULING": conv.sub_ruling_re, "SUB_CLOSURE": conv.sub_closure_re,
            "VERDICTS": conv.verdicts,
            "PAID_RE": conv.paid_for_by_re,
            "CLAIM_FAMILIES": conv.claim_families,
            "SEEDED": conv.seeded,
            "COUNT_CHECKS": conv.count_checks,
            "PROFILE_FILES": conv.profile_files,
            "LAW_FILES": conv.law_files,
            "PROSE_FILES": conv.prose_files,
            "SUPERSEDE_RE": rec.supersede_re,
            "SUPERSEDE_TITLE_RE": rec.supersede_title_re,
            "CLAIM_SHAPED": _claims.CLAIM_SHAPED,
            "ARC_RE": _claims.ARC_RE,
            # generic mechanism
            "DASH": _text.DASH, "BOLD_LEAD": _text.BOLD_LEAD,
            "DATE_RE": _text.DATE_RE, "SECTION_HDR": _text.SECTION_HDR,
            "NUM_RULE": _text.NUM_RULE, "LIST_ITEM": _text.LIST_ITEM,
            "LIST_LAW": _text.LIST_LAW, "STOPWORDS": _text.STOPWORDS,
            "AMBIGUOUS_SUFFIX": _text.AMBIGUOUS_SUFFIX,
            "one_line": _text.one_line, "strip_md": _text.strip_md,
            "github_slug": _text.github_slug, "find_date": _text.find_date,
            "paragraphs": _text.paragraphs,
            "bold_lead_title": _text.bold_lead_title,
            "list_items": _text.list_items,
            "fts_terms": _text.fts_terms, "fts_or": _text.fts_or,
            "SCHEMA": _index.SCHEMA,
            "_sequence_numbers": _index._sequence_numbers,
            "_sequence_gaps": _index._sequence_gaps,
            # verbs, bound
            "build": self.build, "verify": self.verify, "claims": self.claims,
            "query": self.query,
            "read": lambda rel: self.record().read(rel),
            "lines_of": lambda rel: self.record().lines_of(rel),
            "record_markdown": lambda: self.record().record_markdown(),
            "sweep_markdown": lambda: self.record().sweep_markdown(),
            "ruling_documents": lambda: [
                (a, r) for a, _e, r in self.record().ruling_documents()],
            "handoff_documents": lambda: [
                (a, r) for a, _e, r in self.record().handoff_documents()],
            "classify": lambda h: self.record().classify(h),
            "classify_document": lambda rel, line: _claims.classify_document(
                self.record(), rel, line),
            "parse_rulings": lambda: self.record().parse_rulings(),
            "parse_laws": lambda: self.record().parse_laws(),
            "parse_experiments": lambda: self.record().parse_experiments(),
            "parse_handoffs": lambda: self.record().parse_handoffs(),
            "parse_decisions": lambda: self.record().parse_decisions(),
            "parse_prose": lambda s=None: self.record().parse_prose(s),
            "survivable_stdout": _index.survivable_stdout,
        }


class _UnboundConventions(object):
    """What an adapter has before a corpus is found: its own identity, nothing
    about any document.

    Every field that describes a DOCUMENT raises; the three that describe the
    COMMAND do not. That split is the whole point - see `bind`.
    """

    def __init__(self, name, db_rel, db_env):
        self.name, self.db_rel, self.db_env = name, db_rel, db_env

    def __getattr__(self, item):
        raise RootNotFound(
            "no record corpus is bound, so nothing is declared about %r. Run "
            "this from inside a checkout of the record it serves, or pass --db "
            "to work against an index directly." % item)


def bind(adapter_file, conventions_rel=CONVENTIONS_REL, mechanism=None,
         root=None, name=None, db_rel=None, db_env=None):
    """Resolve a record root and load its declaration.

    `adapter_file` is the consuming module's `__file__`; its parent directory's
    parent is the first root candidate, which is what makes a source checkout
    resolve exactly as it always did.

    ⚑ AN UNRESOLVABLE ROOT IS NOT AN IMPORT ERROR. A first draft raised here,
    and that broke a measured, expensive property: an INSTALLED copy with no
    corpus beside it must still answer `--help` and still run `q --db <path>`,
    because the env var and the `--db` flag select an INDEX and never a corpus.
    Raising at import took both of those down - and it took them down at the one
    moment a user is most likely to be running the thing for the first time.
    Four releases once shipped a resolver defect that only `--help` could have
    caught; raising in the importer is the same lesson with the arrow reversed.

    So: root None is a legal state. The refusal is deferred to the first thing
    that actually needs a document, and the fallback identity the caller passes
    keeps the command surface alive until then.
    """
    here = os.path.dirname(os.path.abspath(adapter_file))
    probe = os.path.join(here, os.pardir, conventions_rel.replace("/", os.sep))
    markers = ("CLAUDE.md",)
    if os.path.exists(probe):
        markers = load(probe).markers
    if root is None:
        root = resolve_root(here, markers)
    if root is None:
        return Binding(None,
                       _UnboundConventions(name or "record", db_rel or "",
                                           db_env or "RECORD_INDEX_DB"),
                       mechanism)
    conv = load(os.path.join(root, conventions_rel.replace("/", os.sep)))
    return Binding(root, conv, mechanism)
