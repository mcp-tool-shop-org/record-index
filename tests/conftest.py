"""Shared fixtures for record-index's own suite.

TWO FIXTURE RECORD REPOS, and the second one is not a copy. `alpha` and `beta`
disagree on almost everything a declaration can disagree about - the markers, the
corpus root, the word for a ruling, both arc rules, the verdict vocabulary, the
authority word, the artifact extensions, the phrasing families, the location of
the declaration itself. A suite with one fixture repo cannot tell a declared
convention from a hard-coded one, because every value would be right for the
same reason.

THE COMMITTED FIXTURES ARE READ-ONLY. An autouse guard hashes both trees around
every test: a test that needs to mutate a corpus copies it into tmp_path first,
and one that forgets is named by the guard rather than silently corrupting the
inputs of every test after it.
"""
import hashlib
import io
import os
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FIXTURES = os.path.join(HERE, "fixtures")

ALPHA = os.path.join(FIXTURES, "alpha")
BETA = os.path.join(FIXTURES, "beta")

#: where each fixture repo keeps its declaration, relative to its own root. They
#: differ on purpose: the path is a parameter of `bind`, not a constant.
ALPHA_CONV_REL = "docs/index/conventions.json"
BETA_CONV_REL = "index/conventions.json"

# Import the installed package when there is one - CI installs with `pip install
# -e .` and testing the installed import is the point. Fall back to the checkout
# only when no install is present, so a local run works without hiding a
# packaging failure from CI, where the install always happens first.
try:  # pragma: no cover - exercised by whichever branch the environment takes
    import record_index  # noqa: F401
except ImportError:  # pragma: no cover
    sys.path.insert(0, REPO)

import record_index                                            # noqa: E402
from record_index.conventions import load                      # noqa: E402

#: The package directory as IMPORTED, not as laid out in the checkout. The
#: source-scanning tests read the code this run actually loaded, so an installed
#: copy and a checkout copy can never diverge under them without being seen.
PKG = os.path.dirname(os.path.abspath(record_index.__file__))


# ---------------------------------------------------------------------------
# the read-only guard
# ---------------------------------------------------------------------------

def tree_hashes(root):
    """{relative path: sha256} for every file under a tree, sorted walk."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root).replace("\\", "/")] = \
                    hashlib.sha256(fh.read()).hexdigest()
    return out


@pytest.fixture(autouse=True)
def _fixture_corpora_are_read_only():
    """The committed corpora come back untouched, or the test that moved them
    is named. A suite whose inputs drift under it measures nothing after the
    first mutation."""
    before = (tree_hashes(ALPHA), tree_hashes(BETA))
    yield
    after = (tree_hashes(ALPHA), tree_hashes(BETA))
    for name, b, a in (("alpha", before[0], after[0]), ("beta", before[1], after[1])):
        assert a == b, (
            "a test modified the committed %s fixture tree - the fixtures are "
            "consumed, never edited. Copy with `copy_fixture` and mutate the "
            "copy. changed/added/removed: %s"
            % (name, sorted(set(a) ^ set(b))
                     or sorted(k for k in a if a[k] != b.get(k))))


# ---------------------------------------------------------------------------
# the corpora
# ---------------------------------------------------------------------------

@pytest.fixture
def alpha_conv():
    return load(os.path.join(ALPHA, ALPHA_CONV_REL.replace("/", os.sep)))


@pytest.fixture
def beta_conv():
    return load(os.path.join(BETA, BETA_CONV_REL.replace("/", os.sep)))


@pytest.fixture
def alpha(alpha_conv):
    return record_index.Binding(ALPHA, alpha_conv)


@pytest.fixture
def beta(beta_conv):
    return record_index.Binding(BETA, beta_conv)


@pytest.fixture
def alpha_db(alpha, tmp_path):
    """alpha's index, built once into tmp_path. Never beside the corpus: the
    fixture tree is read-only and a db written into it would trip the guard."""
    db = str(tmp_path / "alpha.db")
    alpha.build(db, quiet=True)
    return db


@pytest.fixture
def beta_db(beta, tmp_path):
    db = str(tmp_path / "beta.db")
    beta.build(db, quiet=True)
    return db


@pytest.fixture
def copy_fixture(tmp_path):
    """Copy a committed fixture repo into tmp_path. Every mutation test starts
    here; nothing mutates a committed tree."""
    def _copy(name="alpha", dest=None):
        src = ALPHA if name == "alpha" else BETA
        out = str(tmp_path / (dest or name))
        shutil.copytree(src, out)
        return out
    return _copy


# ---------------------------------------------------------------------------
# the adapter a consuming repo writes, generated for subprocess tests
# ---------------------------------------------------------------------------

#: What a consuming repo's four-line adapter looks like - the same shape facet's
#: `tools/facet_index.py` uses. Generated rather than committed because the
#: subprocess tests need one INSIDE a copied corpus, at the path `bind` resolves
#: a root from: `<root>/tools/<name>.py`, whose parent's parent is the root.
ADAPTER = '''\
import sys
sys.path.insert(0, %(repo)r)
import record_index
from record_index import cli as _cli

BINDING = record_index.bind(__file__, conventions_rel=%(conv_rel)r,
                            name=%(name)r, db_rel=%(db_rel)r, db_env=%(db_env)r)
globals().update(BINDING.exports())


def main(argv=None):
    return _cli.run_contract(lambda a: _cli.main(BINDING, a), argv,
                             db_env=BINDING.conv.db_env)


if __name__ == "__main__":
    sys.exit(main())
'''


def write_adapter(root, name="alpha", conv_rel=ALPHA_CONV_REL,
                  db_rel="docs/index/alpha.db", db_env="ALPHA_INDEX_DB"):
    """Write a consuming repo's adapter into `<root>/tools/` and return its path."""
    tools = os.path.join(root, "tools")
    if not os.path.isdir(tools):
        os.makedirs(tools)
    p = os.path.join(tools, "%s_index.py" % name)
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(ADAPTER % {"repo": REPO, "conv_rel": conv_rel, "name": name,
                            "db_rel": db_rel, "db_env": db_env})
    return p


@pytest.fixture
def adapter(copy_fixture):
    """A copied corpus with an adapter in it: (root, adapter_path)."""
    def _make(name="alpha"):
        root = copy_fixture(name)
        if name == "alpha":
            return root, write_adapter(root)
        return root, write_adapter(root, "beta", BETA_CONV_REL,
                                   "index/beta.db", "BETA_INDEX_DB")
    return _make
