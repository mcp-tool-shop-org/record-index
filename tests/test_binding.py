"""__init__.py - resolving a record root, and what an adapter gets when there
isn't one.

AN UNRESOLVABLE ROOT IS NOT AN IMPORT ERROR. A first draft raised here, and that
broke a measured property: an INSTALLED copy with no corpus beside it must still
answer `--help` and still run `q --db <path>`, because the env var and the `--db`
flag select an INDEX and never a corpus. Raising at import took both down - at
the one moment a user is most likely to be running the thing for the first time.

So `root is None` is a legal state, the refusal is deferred to the first thing
that actually needs a document, and the fallback identity keeps the command
surface alive until then. Everything below is about that split.
"""
import io
import os

import pytest

import record_index
from record_index import RootNotFound
from record_index.conventions import ConventionsError
from record_index.mechanism import Mechanism


# ---------------------------------------------------------------------------
# is_record_root - the property, not a proxy
# ---------------------------------------------------------------------------

def test_a_directory_carrying_every_marker_is_the_record(alpha):
    assert record_index.is_record_root(alpha.root, alpha.conv.markers)


def test_one_marker_is_not_enough(tmp_path):
    """TWO markers, and the second is not decoration: `CLAUDE.md` alone is an
    ordinary filename and many directories carry one. A single-marker resolver
    would bind a working directory that is some other repo entirely and then
    fail deeper in."""
    d = tmp_path / "impostor"
    d.mkdir()
    (d / "CLAUDE.md").write_text("an ordinary file", encoding="utf-8")
    assert not record_index.is_record_root(str(d), ("CLAUDE.md", "docs/experiments"))
    assert record_index.is_record_root(str(d), ("CLAUDE.md",))


def test_the_markers_are_declared_so_the_two_repos_disagree(alpha, beta):
    """beta is not marked by CLAUDE.md at all. A resolver keyed on a
    conventional filename would bind nothing there."""
    assert record_index.is_record_root(beta.root, beta.conv.markers)
    assert not record_index.is_record_root(beta.root, alpha.conv.markers)
    assert not record_index.is_record_root(alpha.root, beta.conv.markers)


def test_a_marker_path_with_a_separator_is_resolved_per_platform(alpha):
    assert record_index.is_record_root(alpha.root, ("docs/experiments",))


def test_an_empty_path_is_not_a_record_root():
    assert not record_index.is_record_root("", ("CLAUDE.md",))
    assert not record_index.is_record_root(None, ("CLAUDE.md",))


# ---------------------------------------------------------------------------
# resolve_root - most specific first, and no walk up
# ---------------------------------------------------------------------------

def test_resolve_takes_the_first_candidate_that_holds(alpha, tmp_path,
                                                      monkeypatch):
    here = os.path.join(alpha.root, "tools")
    monkeypatch.chdir(str(tmp_path))
    assert record_index.resolve_root(here, alpha.conv.markers) == \
        os.path.abspath(alpha.root)


def test_resolve_falls_through_to_the_working_directory(alpha, tmp_path,
                                                        monkeypatch):
    """Which is where an INSTALLED command is run from."""
    monkeypatch.chdir(alpha.root)
    nowhere = str(tmp_path / "elsewhere" / "tools")
    assert record_index.resolve_root(nowhere, alpha.conv.markers) == \
        os.path.abspath(alpha.root)


def test_resolve_refuses_rather_than_returning_a_plausible_path(tmp_path,
                                                                monkeypatch):
    """None, never a guess. Returning a plausible-looking directory only moves
    the failure one caller downstream."""
    monkeypatch.chdir(str(tmp_path))
    assert record_index.resolve_root(str(tmp_path / "x" / "tools"),
                                     ("CLAUDE.md", "docs/experiments")) is None


def test_there_is_no_walk_up_from_the_working_directory(alpha, tmp_path,
                                                        monkeypatch):
    """A walk up would resolve a SUBDIRECTORY of a checkout, and would also
    reach a parent that is a DIFFERENT record. Here the working directory is
    inside alpha's own checkout and neither candidate holds, so the answer is a
    refusal rather than alpha's root one level up."""
    monkeypatch.chdir(os.path.join(alpha.root, "docs", "experiments"))
    nowhere = str(tmp_path / "elsewhere" / "tools")
    assert record_index.resolve_root(nowhere, alpha.conv.markers) is None


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------

def test_bind_resolves_a_checkout_from_an_adapters_own_file(adapter):
    root, path = adapter("alpha")
    b = record_index.bind(path)
    assert b.root == os.path.abspath(root)
    assert b.conv.name == "alpha"


def test_bind_reads_the_declaration_from_the_declared_location(adapter):
    """The path to a repo's declaration is a parameter, not a constant: beta
    keeps its own at index/conventions.json."""
    root, path = adapter("beta")
    b = record_index.bind(path, conventions_rel="index/conventions.json")
    assert b.root == os.path.abspath(root)
    assert b.conv.name == "beta"


def test_bind_with_no_corpus_returns_a_binding_rather_than_raising(tmp_path,
                                                                   monkeypatch):
    monkeypatch.chdir(str(tmp_path))
    d = tmp_path / "installed"
    d.mkdir()
    b = record_index.bind(str(d / "somewhere.py"), name="tool",
                          db_rel="x/y.db", db_env="TOOL_DB")
    assert b.root is None
    assert b.conv.name == "tool"
    assert b.conv.db_rel == "x/y.db"
    assert b.conv.db_env == "TOOL_DB"


def test_the_unbound_declaration_refuses_every_field_about_a_document(
        tmp_path, monkeypatch):
    """Every field that describes a DOCUMENT raises; the three that describe the
    COMMAND do not. That split is the whole point."""
    monkeypatch.chdir(str(tmp_path))
    b = record_index.bind(str(tmp_path / "x.py"), name="tool")
    for item in ("markers", "verdicts", "ruling_doc_re", "seeded"):
        with pytest.raises(RootNotFound) as exc:
            getattr(b.conv, item)
        assert item in str(exc.value)
        assert "--db" in str(exc.value), "the refusal does not name the way out"


def test_a_resolved_root_with_no_declaration_refuses_at_bind_time(tmp_path,
                                                                  monkeypatch):
    """MEASURED, and pinned as measured. An unresolvable ROOT is a legal state;
    a resolved root carrying no declaration is a different case and it raises
    ConventionsError out of `bind` - which means out of a consuming adapter's
    import. The refusal names the file it looked for."""
    monkeypatch.chdir(str(tmp_path))
    root = tmp_path / "half"
    (root / "tools").mkdir(parents=True)
    (root / "CLAUDE.md").write_text("a law book and nothing else", encoding="utf-8")
    with pytest.raises(ConventionsError) as exc:
        record_index.bind(str(root / "tools" / "adapter.py"))
    assert "conventions.json" in str(exc.value)


def test_bind_accepts_an_explicit_root(alpha):
    b = record_index.bind(os.path.join(alpha.root, "tools", "x.py"),
                          root=alpha.root)
    assert b.root == alpha.root


def test_bind_carries_a_mechanism_through(alpha):
    m = Mechanism(CANDIDATES=9)
    b = record_index.bind(os.path.join(alpha.root, "tools", "x.py"),
                          root=alpha.root, mechanism=m)
    assert b.mech is m


# ---------------------------------------------------------------------------
# the root is read through a provider
# ---------------------------------------------------------------------------

def test_the_root_is_read_through_the_provider_on_every_access(alpha):
    """NOT CAPTURED, and the reason is a real one a first draft got wrong. A
    consuming repo's suite points the corpus gate at an empty directory by
    monkeypatching the adapter module's global; a Binding that captured the root
    at construction made that patch a no-op, so twelve resolver tests went green
    against a value they were no longer setting."""
    state = {"root": alpha.root}
    b = record_index.Binding(alpha.root, alpha.conv)
    b.set_root_provider(lambda: state["root"])
    assert b.root == alpha.root
    state["root"] = None
    assert b.root is None, "the Binding captured the root instead of reading it"


def test_set_root_provider_returns_the_binding_for_chaining(alpha):
    b = record_index.Binding(alpha.root, alpha.conv)
    assert b.set_root_provider(lambda: alpha.root) is b


def test_the_record_follows_the_provider(alpha):
    state = {"root": alpha.root}
    b = record_index.Binding(alpha.root, alpha.conv).set_root_provider(
        lambda: state["root"])
    assert b.record().root == alpha.root
    state["root"] = "/somewhere/else"
    assert b.record().root == "/somewhere/else"


# ---------------------------------------------------------------------------
# exports - the surface a consuming adapter re-exports
# ---------------------------------------------------------------------------

def test_the_bound_surface_carries_the_declared_patterns(alpha):
    """Surfaced as module attributes so a repo's own tests can assert against
    the conventions it declared."""
    e = alpha.exports()
    assert e["REPO"] == alpha.root
    assert e["RECORD_MARKERS"] == alpha.conv.markers
    assert e["RULING_HDR"] is alpha.conv.ruling_hdrs[0]
    assert e["VERDICTS"] == alpha.conv.verdicts
    assert e["DB_REL"] == "docs/index/alpha.db"
    assert e["DB_ENV"] == "ALPHA_INDEX_DB"
    assert callable(e["build"]) and callable(e["verify"])
    assert callable(e["query"]) and callable(e["claims"])


def test_the_unbound_surface_is_the_command_half_only(tmp_path, monkeypatch):
    """`--help` and a `--db`-explicit `q` need exactly the first half, and none
    of the declared patterns, because there is no declaration to surface."""
    monkeypatch.chdir(str(tmp_path))
    e = record_index.bind(str(tmp_path / "x.py"), name="tool", db_rel="a/b.db",
                          db_env="TOOL_DB").exports()
    assert e["REPO"] is None
    assert e["DB_REL"] == "a/b.db"
    assert e["EXIT_REFUSED"] == 4
    assert callable(e["one_line"]) and callable(e["fts_terms"])
    for declared in ("RULING_HDR", "VERDICTS", "SEEDED", "CLAIM_FAMILIES"):
        assert declared not in e


def test_both_surfaces_carry_every_exit_code(alpha, tmp_path, monkeypatch):
    monkeypatch.chdir(str(tmp_path))
    unbound = record_index.bind(str(tmp_path / "x.py"), name="t").exports()
    for e in (alpha.exports(), unbound):
        assert (e["EXIT_OK"], e["EXIT_USER"], e["EXIT_RUNTIME"],
                e["EXIT_PARTIAL"], e["EXIT_REFUSED"]) == (0, 1, 2, 3, 4)


def test_the_exported_surface_is_named_explicitly_and_not_swept(alpha):
    """An adapter's surface is a contract other tools and tests bind to, and a
    surface derived from whatever happened to be public is not one. Nothing
    private leaks except the two sequence helpers, which are exported by name."""
    e = alpha.exports()
    private = sorted(k for k in e if k.startswith("_"))
    assert private == ["_sequence_gaps", "_sequence_numbers"]


def test_the_exported_verbs_are_bound_to_this_binding(alpha, tmp_path):
    e = alpha.exports()
    e["build"](str(tmp_path / "via_export.db"), quiet=True)
    assert os.path.exists(str(tmp_path / "via_export.db"))


def test_the_exported_readers_reach_this_repos_files(alpha):
    e = alpha.exports()
    assert "# alpha" in e["read"]("OVERVIEW.md")
    assert e["lines_of"]("OVERVIEW.md")[0] == "# alpha"
    assert "docs/experiments/E01-ruling.md" in e["record_markdown"]()


def test_the_two_repos_export_different_declared_patterns(alpha, beta):
    a, b = alpha.exports(), beta.exports()
    assert a["RULING_DOC_RE"].pattern != b["RULING_DOC_RE"].pattern
    assert a["VERDICTS"] != b["VERDICTS"]
    assert a["ADDENDA_HDR"] is not None and b["ADDENDA_HDR"] is None
    assert a["AMEND_HDR"] is not None and b["AMEND_HDR"] is None


# ---------------------------------------------------------------------------
# db_default
# ---------------------------------------------------------------------------

def test_db_default_is_the_declared_path_under_the_root(alpha):
    assert alpha.db_default() == os.path.join(
        alpha.root, "docs", "index", "alpha.db")


def test_each_repo_has_its_own_default_and_its_own_env_var(alpha, beta):
    assert os.path.basename(alpha.db_default()) == "alpha.db"
    assert os.path.basename(beta.db_default()) == "beta.db"
    assert alpha.conv.db_env != beta.conv.db_env


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

def test_the_package_declares_a_version():
    assert record_index.__version__ == "0.1.0"
