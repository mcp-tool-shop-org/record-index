"""text.py - the generic markdown and English mechanism.

NOTHING HERE IS A FACT ABOUT A REPO, and that is the claim under test. Each
function is exercised on inputs drawn from both fixture corpora, whose house
styles have nothing in common, plus the specific shapes the module's own comments
say were measured: the three dashes, the wrapped bold run, the list with no blank
lines, the shell-variable prefix that once minted a phantom artifact.
"""
import re

import pytest

from record_index import text as T
from record_index.mechanism import DEFAULT


# ---------------------------------------------------------------------------
# one_line
# ---------------------------------------------------------------------------

def test_one_line_collapses_whitespace_and_trims_dots():
    assert T.one_line("  a  holding\n   over  two lines .  ") == \
        "a holding over two lines"


def test_one_line_truncates_at_the_limit_and_says_so():
    long = "x" * 400
    got = T.one_line(long)
    assert len(got) == DEFAULT.ONE_LINE_LIMIT
    assert got.endswith("…")


def test_one_line_at_exactly_the_limit_is_not_truncated():
    """THE BOUNDARY, both sides. A truncation test that only ever fed 400
    characters could not tell `>` from `>=`."""
    exact = "x" * DEFAULT.ONE_LINE_LIMIT
    assert T.one_line(exact) == exact
    over = "x" * (DEFAULT.ONE_LINE_LIMIT + 1)
    assert T.one_line(over) != over and over.startswith(T.one_line(over)[:-1])


def test_one_line_takes_an_explicit_limit():
    assert T.one_line("abcdefghij", limit=5) == "abcd…"


# ---------------------------------------------------------------------------
# strip_md
# ---------------------------------------------------------------------------

def test_strip_md_removes_markup_and_keeps_the_words():
    got = T.strip_md("**bold** and *italic* and `code` and [link](http://x/) and > q")
    assert got == "bold and italic and code and link and   q"


def test_strip_md_leaves_a_bare_word_alone():
    assert T.strip_md("nothing to strip") == "nothing to strip"


# ---------------------------------------------------------------------------
# the dash class
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dash", ["—", "–", "-"])
def test_all_three_dashes_are_one_class(dash):
    """A record's prose uses all three and a class tolerating only one silently
    loses every row written with the others."""
    assert re.match(T.DASH, dash)


# ---------------------------------------------------------------------------
# dates
# ---------------------------------------------------------------------------

def test_find_date_takes_the_first_iso_date():
    assert T.find_date("written 2026-01-05, folded 2026-02-09") == "2026-01-05"


def test_find_date_returns_none_rather_than_guessing():
    assert T.find_date("no date here at all, only 12/05 and 2026") is None


# ---------------------------------------------------------------------------
# paragraphs
# ---------------------------------------------------------------------------

def test_paragraphs_split_on_blank_lines_with_true_line_numbers():
    lines = ["one", "still one", "", "two", "", "", "three"]
    got = T.paragraphs(lines, 0)
    assert got == [(0, ["one", "still one"]), (3, ["two"]), (6, ["three"])]


def test_paragraphs_offsets_by_the_start_line():
    got = T.paragraphs(["a", "", "b"], 10)
    assert [start for start, _ in got] == [10, 12]


def test_paragraphs_handles_leading_and_trailing_blanks():
    assert T.paragraphs(["", "a", ""], 0) == [(1, ["a"])]
    assert T.paragraphs([], 0) == []


# ---------------------------------------------------------------------------
# bold_lead_title
# ---------------------------------------------------------------------------

def test_bold_lead_closes_across_wrapped_lines():
    """The bold run may span several wrapped lines, so the closer is searched
    across the whole paragraph rather than on the first line."""
    title, rest = T.bold_lead_title(["**a title that wraps", "onto a second line**",
                                     "and then the body."])
    assert title == "a title that wraps\nonto a second line"
    assert rest.strip() == "and then the body."


def test_a_paragraph_not_opening_in_bold_is_not_a_title():
    assert T.bold_lead_title(["ordinary prose with **bold** inside"]) == (None, None)


def test_an_unclosed_bold_run_is_not_a_title():
    """An opener with no closer returns nothing rather than swallowing the rest
    of the document as a title."""
    assert T.bold_lead_title(["**an opener", "that never closes"]) == (None, None)


# ---------------------------------------------------------------------------
# list_items - the law shape
# ---------------------------------------------------------------------------

def test_a_run_of_bold_list_items_with_no_blank_lines_splits_into_items():
    """Measured, not assumed: lists carry no blank line between items, so ten
    numbered rules read as one block and a blank-line splitter captures only the
    first."""
    par = ["1. **first rule.** body",
           "2. **second rule.** body",
           "3. **third rule.** body",
           "   wrapped onto a second line"]
    got = T.list_items(par)
    assert len(got) == 3
    assert got[2] == ["3. **third rule.** body", "   wrapped onto a second line"]


def test_prose_that_merely_begins_with_a_marker_is_not_cut_into_phantom_laws():
    """Requiring the `**` immediately after the marker is what keeps an ordinary
    bulleted sentence from minting a law."""
    par = ["- an ordinary bullet", "- another one"]
    assert T.list_items(par) == [par]


# ---------------------------------------------------------------------------
# fts_terms
# ---------------------------------------------------------------------------

def test_fts_terms_drops_stopwords_and_single_characters():
    assert T.fts_terms("what is the depth pass a b") == ["depth", "pass"]


def test_fts_terms_never_returns_empty():
    """A query of nothing but stopwords keeps them rather than producing an
    empty MATCH, which sqlite would refuse."""
    assert T.fts_terms("the is of and") == ["the", "is", "of", "and"]


def test_fts_or_quotes_every_term():
    assert T.fts_or("depth pass") == '"depth" OR "pass"'


def test_stopwords_are_ordinary_function_words_not_record_vocabulary():
    """GENERIC BY CONSTRUCTION. If a word from either fixture's own vocabulary
    were in here, the list would be a fact about a record wearing a fact about
    English."""
    for w in ("ruling", "decision", "accepted", "upheld", "arc", "handoff"):
        assert w not in T.STOPWORDS


# ---------------------------------------------------------------------------
# artifact_pattern - declared extensions, and the two false-positive shapes
# ---------------------------------------------------------------------------

def test_artifact_pattern_matches_only_declared_extensions():
    rx = T.artifact_pattern(["png", "glb"])
    assert rx.search("see outputs/a/b.png").group(1) == "outputs/a/b.png"
    assert rx.search("see outputs/a/b.mp4") is None


def test_artifact_pattern_reads_a_windows_path():
    rx = T.artifact_pattern(["png"])
    assert rx.search(r"see outputs\a\b.png").group(1) == r"outputs\a\b.png"


def test_a_shell_variable_prefix_is_not_swallowed_into_the_path():
    """Measured: `$` and `%` are excluded from the lookbehind so a variable
    prefix does not mint a phantom artifact called `j/inpainted.png`."""
    rx = T.artifact_pattern(["png"])
    assert rx.search("$j/inpainted.png") is None
    assert rx.search("%j%/inpainted.png") is None


def test_the_extension_alternation_is_escaped():
    """The alternation is built from declared strings; a declaration carrying a
    regex metacharacter must be matched literally rather than compiled."""
    rx = T.artifact_pattern(["p.g"])
    assert rx.search("file.p.g") is not None
    assert rx.search("file.png") is None


# ---------------------------------------------------------------------------
# supersede_patterns - conservative by design
# ---------------------------------------------------------------------------

def test_supersede_reads_an_explicit_verb_over_declared_verbs():
    explicit, _ = T.supersede_patterns(["CORRECTED", "corrected"])
    assert explicit.findall("Ruling 1 is CORRECTED in place") == ["1"]


def test_supersede_declines_to_guess_at_a_verb_nobody_declared():
    """A phrase these do not match is UNDER-counted, never mis-attributed."""
    explicit, _ = T.supersede_patterns(["CORRECTED"])
    assert explicit.findall("Ruling 1 is quietly rethought") == []
    assert explicit.findall("Ruling 1 is OVERTURNED") == []


def test_the_title_form_requires_adjacency():
    """Adjacency is what keeps a correction from being attributed to whichever
    number happened to appear earlier in the sentence: the number must sit
    immediately before the verb, with nothing but whitespace between."""
    _, title = T.supersede_patterns(["CORRECTED"])
    assert title.findall("25c is CORRECTED IN PLACE") == ["25c"]
    assert title.findall("9 is WITHDRAWN") == ["9"]
    assert title.findall("25c, and separately 9, is WITHDRAWN") == []
    assert title.findall("25c and the whole of 9 are gone") == []


def test_a_declared_verb_set_that_omits_a_verb_does_not_match_it():
    """beta declares OVERTURNED and not CORRECTED; alpha the reverse. A pattern
    built from one repo's verbs must be silent on the other's."""
    beta_explicit, _ = T.supersede_patterns(["OVERTURNED", "overturned"])
    assert beta_explicit.findall("Ruling 2 is OVERTURNED") == ["2"]
    assert beta_explicit.findall("Ruling 2 is CORRECTED in place") == []


# ---------------------------------------------------------------------------
# github_slug
# ---------------------------------------------------------------------------

def test_github_slug_lowercases_strips_markup_and_hyphenates():
    """GitHub's algorithm runs on the heading TEXT. Handed a whole heading LINE
    it keeps the space the stripped hashes leave behind and mints a leading
    hyphen, which is measured here rather than assumed away."""
    assert T.github_slug("The **Depth** Pass, ratified") == \
        "the-depth-pass-ratified"
    assert T.github_slug("## The **Depth** Pass, ratified") == \
        "-the-depth-pass-ratified"
