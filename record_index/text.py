"""Generic markdown and text mechanism. Nothing here is a fact about a repo.

Everything in this file was classified GENERIC by measurement, not by reading:
each was run against a second record repo unchanged. The dash class, the ISO
date, the markdown heading and list shapes, the stopword list and the GitHub
slug algorithm are conventions of markdown and of English, not of any record.
"""
import re
import unicodedata

from .mechanism import DEFAULT

#: em dash, en dash, hyphen - a record's prose uses all three, and a class that
#: tolerates only one silently loses rows written with the others.
DASH = "[—–-]"

BOLD_LEAD = re.compile(r"^\*\*")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
SECTION_HDR = re.compile(r"^(#{2,3}) +(.*)$")
NUM_RULE = re.compile(r"^(\d+)\. +\*\*")
LIST_ITEM = re.compile(r"^(?:\d+\.|[-*]) +")
LIST_LAW = re.compile(r"^(?:\d+\.|[-*]) +\*\*")
RELEASED_RE = re.compile(r"^## \[\d+\.\d+\.\d+\]")
AMBIGUOUS_SUFFIX = re.compile(r"\+\s*the\s+close|\bso far\b|\bat least\b|\bor so\b")
COMMIT_RE = re.compile(r"`([0-9a-f]{7,40})`")

#: Ordinary English function words. Measured on a real corpus before they were
#: removed: "the" appeared in 94.9% of indexed rows, "is" in 77.9%, "not" in
#: 62.2%, so an OR query carrying them matches nearly everything and the
#: discriminating term is one weak signal among many. GENERIC by construction -
#: not derived from any question in any seeded set.
STOPWORDS = frozenset("""
a an and are as at be been but by can did do does for from had has have how i if in
into is it its of on or our so than that the their them then there these they this
to was we were what when where which who why will with would you your not no nor
""".split())


def one_line(text, limit=None):
    """Collapse to a single line. Holdings are quoted in query output."""
    limit = DEFAULT.ONE_LINE_LIMIT if limit is None else limit
    t = re.sub(r"\s+", " ", text).strip()
    t = t.strip(" .")
    if len(t) > limit:
        t = t[: limit - 1].rstrip() + "…"
    return t


def strip_md(text):
    """Remove the markup that would otherwise be indexed as words."""
    t = text
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\*\*([^*]*)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]*)\*", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = t.replace(">", " ")
    return t


def github_slug(heading):
    """GitHub's heading anchor algorithm, for `#`-headings only."""
    s = unicodedata.normalize("NFKD", heading)
    s = strip_md(s).strip().lower()
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s)
    return s


def find_date(text):
    m = DATE_RE.search(text)
    return m.group(1) if m else None


def paragraphs(block_lines, start_line):
    """Split a run of lines into (start_line_number, [lines]) paragraphs.

    A paragraph boundary is a blank line. This is the discriminator that keeps a
    wrapped `**word**` mid-sentence from being read as a bold-lead heading.
    """
    out = []
    cur = []
    cur_start = start_line
    for i, ln in enumerate(block_lines):
        if ln.strip() == "":
            if cur:
                out.append((cur_start, cur))
                cur = []
            cur_start = start_line + i + 1
        else:
            if not cur:
                cur_start = start_line + i
            cur.append(ln)
    if cur:
        out.append((cur_start, cur))
    return out


def bold_lead_title(par_lines):
    """Return (title, rest) for a paragraph opening with `**`, else (None, None).

    The bold run may span several wrapped lines, so the closing `**` is searched
    across the whole paragraph. An opener with no closer returns (None, None)
    rather than swallowing the rest of the document as a title.
    """
    text = "\n".join(par_lines)
    if not text.startswith("**"):
        return None, None
    end = text.find("**", 2)
    if end < 0:
        return None, None
    return text[2:end], text[end + 2:]


def list_items(par):
    """Split a paragraph wherever a list item OPENS IN BOLD - the law shape.

    Two properties of a law corpus make a plain blank-line splitter lose most of
    it, and both were measured rather than assumed: lists carry no blank line
    between items, so ten numbered rules read as one block and only the first is
    captured; and an item may itself CONTAIN a blank line, after which later
    items sit in a block that no longer starts with a marker.

    Requiring the `**` immediately after the marker keeps prose that merely
    begins a line with `- ` from being cut into phantom laws.
    """
    if not any(LIST_LAW.match(ln) for ln in par):
        return [par]
    out, cur = [], []
    for ln in par:
        if LIST_LAW.match(ln) and cur:
            out.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        out.append(cur)
    return out


def fts_terms(phrase):
    """Content words of a query phrase, lowercased, stopwords dropped."""
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_.'-]*", phrase)
             if len(w) > 1]
    kept = [w for w in words if w not in STOPWORDS]
    return kept or words          # never return an empty query


def fts_or(phrase):
    return " OR ".join('"%s"' % w for w in fts_terms(phrase))


def artifact_pattern(extensions):
    """The path-shaped-token pattern, over a DECLARED extension set.

    A record writes Windows paths with backslashes and shell fragments with
    variable prefixes; both are matched, and `$`/`%` are excluded from the
    lookbehind so a variable prefix is not swallowed into the path (which would
    mint a phantom artifact called `j/inpainted.png`).

    The extension alternation is declared rather than built in: it is the set of
    things a particular pipeline produces, and one pipeline's is not another's.
    """
    # Concatenated, NOT %-formatted: the lookbehind contains a literal `%` (to
    # keep a shell variable prefix out of the path) and %-formatting reads it as
    # a conversion. Caught on the first build against a real record.
    alternation = "|".join(re.escape(e) for e in extensions)
    return re.compile(
        r"(?<![\w/\\.$%-])((?:[A-Za-z0-9_][A-Za-z0-9_.\-]*[/\\])*"
        r"[A-Za-z0-9_][A-Za-z0-9_.\-]*"
        r"\.(?:" + alternation + r"))(?![\w])")


def supersede_patterns(verbs, objects=("Ruling", "Amendment")):
    """(explicit, title-form) correction patterns over DECLARED verbs.

    Conservative by design: a phrase these do not match is under-counted, never
    mis-attributed. The title form requires ADJACENCY between the number and the
    verb, which is what keeps a correction from being attributed to whichever
    number appeared earlier in the sentence.
    """
    verb_alt = "|".join(verbs)
    obj_alt = "|".join(objects)
    explicit = re.compile(
        r"(?:%s)\s+(\d+[a-z]?)(?:'s [^.;:]{0,60}?)?\s+"
        r"(?:is\s+|are\s+)?(?:now\s+)?"
        r"(?:%s)\b" % (obj_alt, verb_alt))
    title = re.compile(
        r"\b(\d+[a-z]?)\s+(?:is\s+)?"
        r"(?:corrected in place|CORRECTED IN PLACE|withdrawn|WITHDRAWN)")
    return explicit, title
