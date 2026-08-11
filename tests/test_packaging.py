"""The packaging contract - what an adopting repo takes on by installing this.

`dependencies = []` IS A DECLARED PROPERTY RATHER THAN AN ACCIDENT, and it is the
whole reason a consuming repo can adopt this package without inheriting a
transitive surface: the index is sqlite3 + re + json, all stdlib. A test suite
that let one dependency in through the back door would be spending the property
the package is sold on, so the check is here rather than in a reviewer's head.

The floor matters for the same reason: `requires-python = ">=3.11"` is a promise
about who can install this, and CI runs the floor and the ceiling.
"""
import ast
import os
import sys
import tomllib

import pytest

import record_index
from conftest import PKG, REPO

PYPROJECT = os.path.join(REPO, "pyproject.toml")
MODULES = sorted(f for f in os.listdir(PKG) if f.endswith(".py"))

#: Everything the package is allowed to import. All stdlib.
STDLIB_ALLOWED = {
    "argparse", "ast", "codecs", "datetime", "hashlib", "io", "json", "os",
    "re", "sqlite3", "sys", "traceback", "unicodedata",
}


@pytest.fixture(scope="module")
def project():
    with open(PYPROJECT, "rb") as fh:
        return tomllib.load(fh)["project"]


def test_the_runtime_dependency_list_is_empty(project):
    """THE DECLARED CONTRACT. A consuming repo installs one package and gets no
    transitive surface."""
    assert project["dependencies"] == []


def test_no_module_imports_anything_outside_the_standard_library():
    """The other end of the same property, from the source rather than from the
    metadata: an empty dependency list beside an import of a third-party module
    is a package that fails to install correctly and says nothing about it."""
    outside = []
    for name in MODULES:
        with open(os.path.join(PKG, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:            # a relative import, inside the package
                    continue
                mods = [(node.module or "").split(".")[0]]
            else:
                continue
            for m in mods:
                if m and m not in STDLIB_ALLOWED:
                    outside.append("%s:%d imports %s" % (name, node.lineno, m))
    assert not outside, "\n".join(outside)


def test_every_import_the_package_makes_resolves_without_installing_anything():
    """The can-fail-adjacent leg: the allow-list above is only meaningful if
    each name on it really is importable from a bare interpreter."""
    import importlib
    for m in sorted(STDLIB_ALLOWED):
        importlib.import_module(m)


def test_the_declared_python_floor_is_the_one_this_suite_targets(project):
    assert project["requires-python"] == ">=3.11"


def test_this_interpreter_is_at_or_above_the_declared_floor(project):
    assert sys.version_info[:2] >= (3, 11)


def test_the_declared_version_and_the_package_version_agree(project):
    """A tag built from one and a wheel reporting the other is a release nobody
    can trace back to a commit."""
    assert project["version"] == record_index.__version__


def test_the_package_is_the_one_declared_for_distribution(project):
    with open(PYPROJECT, "rb") as fh:
        doc = tomllib.load(fh)
    assert doc["tool"]["setuptools"]["packages"] == ["record_index"]
    assert project["name"] == "record-index"


def test_every_module_on_disk_ships(project):
    """`packages = ["record_index"]` ships the directory. A module added to the
    source tree and not to the distribution is the class of defect that only a
    clean-venv install would otherwise find."""
    assert set(MODULES) == {
        "__init__.py", "certificate.py", "claims.py", "cli.py",
        "conventions.py", "index.py", "mechanism.py", "parse.py", "text.py",
        "vocab.py"}


def test_the_license_is_declared_and_the_file_is_there(project):
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert os.path.exists(os.path.join(REPO, "LICENSE"))


def test_the_classifiers_name_the_versions_the_floor_admits(project):
    """A classifier list that stops below what `requires-python` allows
    understates support; one that runs above it overstates it."""
    versions = [c.rsplit(" :: ", 1)[-1] for c in project["classifiers"]
                if c.startswith("Programming Language :: Python :: 3.")]
    assert versions == ["3.11", "3.12", "3.13"]


def test_every_module_compiles(tmp_path):
    """A module that does not compile takes the whole package down at import,
    and a packaging list is the one place that is easy to get wrong quietly."""
    import py_compile
    for name in MODULES:
        py_compile.compile(os.path.join(PKG, name),
                           cfile=str(tmp_path / (name + "c")), doraise=True)
