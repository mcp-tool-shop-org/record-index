"""The gate and the write surface - two properties RE-HOMED from facet's suite.

WHY THEY LIVE HERE NOW. facet's `test_t30_gates_survive_optimize.py` AST-scans
`tools/facet_index.py` for `run_contract` and the ANDON machinery, and
`test_t19_record_mcp_readonly.py` asserts that only the certificate writer
writes. Both properties are intact and neither file is where the code lives any
more: `run_contract`, the andon and the certificate writer are all in this
package. A test that scans a shim is green rather than red, which is worse.

So the package half re-homes here and facet keeps the half that is about facet -
its own instruments' gates, its own ANDON message census, its server's read-only
sqlite handle.

THE TWO PROPERTIES:

  * A GATE IS NEVER A BARE `assert`. `python -O` and `PYTHONOPTIMIZE=1` delete
    one silently and execution continues past it - the gate goes quiet, the
    write proceeds, the process exits 0. Every check that the gate fires under
    `-O` is paired with a proof, on a throwaway script, that `-O` is really
    stripping asserts in this interpreter; without that the legs could all be
    passing for the wrong reason.

  * THE PACKAGE WRITES IN EXACTLY THREE PLACES. `parse.py`'s own first law is
    that it never writes to a record, and an AST scan is how that becomes
    checkable rather than promised. Both directions are demonstrated: every
    assertion about the real source is paired with the same scanner run over a
    synthetic source that violates it.

WHY SUBPROCESS. `__debug__` is fixed when the interpreter starts and cannot be
toggled inside a running process, so an in-process test of this cannot exist.
"""
import ast
import io
import os
import subprocess
import sys

import pytest

from conftest import PKG
from record_index.index import EXIT_OK, EXIT_REFUSED

MODES = [("normal", [], {}),
         ("dash-O", ["-O"], {}),
         ("PYTHONOPTIMIZE", [], {"PYTHONOPTIMIZE": "1"})]
MODE_IDS = [m[0] for m in MODES]

MODULES = sorted(f for f in os.listdir(PKG) if f.endswith(".py"))

STRAY_REL = "docs/experiments/E09-ZZ-stray-handoff.md"
STRAY_BODY = (
    "# a file this test writes into a COPY, to trip the inverse discovery guard\n"
    "\n"
    "## Session handoff 1 (2026-01-01, executor) - invisible to the glob\n"
    "\n"
    "It matches neither the ruling glob nor the kickoff glob, so it is exactly\n"
    "the condition assert_no_undiscovered_handoffs asks about.\n")


def source_of(name):
    with io.open(os.path.join(PKG, name), encoding="utf-8") as fh:
        return fh.read()


def run(flags, script, args, cwd, env_extra=None, timeout=300):
    """One command, one process, with interpreter FLAGS as well as env.

    The flags are the point: `-O` is an interpreter switch, not an env var, and
    a helper that only carried env could not test half of what matters."""
    env = os.environ.copy()
    env.pop("PYTHONOPTIMIZE", None)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable] + list(flags) + [script]
                       + [str(a) for a in args],
                       cwd=cwd, env=env, capture_output=True, timeout=timeout)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# the can-fail leg that makes every -O leg below mean something
# ---------------------------------------------------------------------------

def test_the_optimize_legs_are_not_vacuous(tmp_path):
    """PROOF THAT THE STRIPPING MECHANISM IS LIVE ON THIS INTERPRETER, on a
    script this test writes and throws away - never on a gate of ours. A bare
    `assert` must halt under a normal interpreter and must NOT halt under `-O`
    or `PYTHONOPTIMIZE=1`. If that were untrue here, every `the gate fires under
    -O` below would be passing for the wrong reason.

    This is the opposite of anchoring the defect: it pins a property of CPython,
    on throwaway source, so that the tests of the real gate can be believed."""
    probe = tmp_path / "probe.py"
    probe.write_text("import sys\n"
                     "assert False, 'a bare assert the interpreter may delete'\n"
                     "sys.stdout.write('WALKED PAST\\n')\n",
                     encoding="ascii", newline="\n")
    rc, out, err = run([], str(probe), [], str(tmp_path))
    assert rc != 0 and "WALKED PAST" not in out, (
        "a bare assert did not halt a NORMAL interpreter (rc %d)\n%s%s"
        % (rc, out, err))
    for name, flags, env in MODES[1:]:
        rc, out, err = run(flags, str(probe), [], str(tmp_path), env)
        assert rc == 0 and "WALKED PAST" in out, (
            "%s did not strip a bare assert on this interpreter (rc %d) - so "
            "the -O legs in this file would be vacuous\n%s%s"
            % (name, rc, out, err))


# ---------------------------------------------------------------------------
# the one gate in the package, fired in all three interpreter modes
# ---------------------------------------------------------------------------

@pytest.fixture
def stray(adapter):
    """A copied corpus carrying a handoff header the declared glob cannot
    reach, plus an adapter to run against it."""
    root, path = adapter("alpha")
    p = os.path.join(root, STRAY_REL.replace("/", os.sep))
    with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(STRAY_BODY)
    return root, path


@pytest.mark.parametrize("mode,flags,env", MODES, ids=MODE_IDS)
def test_the_discovery_gate_refuses_in_every_interpreter_mode(stray, tmp_path,
                                                              mode, flags, env):
    root, path = stray
    db = str(tmp_path / "andon.db")
    rc, out, err = run(flags, path, ["build", "--db", db], root, env)
    body = out + err
    assert rc == EXIT_REFUSED, (
        "[%s] the stray handoff exited %d, want %d\n%s" % (mode, rc, EXIT_REFUSED,
                                                           body))
    assert "ANDON:" in body, "[%s] the gate fired without saying so:\n%s" % (mode, body)
    assert "GATE_FIRED" in err, "[%s] %s" % (mode, err)
    assert "E09-ZZ-stray-handoff.md" in body, (
        "[%s] the refusal does not name the file that tripped it:\n%s" % (mode, body))


@pytest.mark.parametrize("mode,flags,env", MODES, ids=MODE_IDS)
def test_the_discovery_gate_can_fail_in_every_interpreter_mode(adapter, tmp_path,
                                                               mode, flags, env):
    """CAN-FAIL LEG: with no stray file the same command in the same mode must
    build and exit 0. Without it, `rc != 0` above would pass equally well on a
    tool that could not run at all under -O."""
    root, path = adapter("alpha")
    db = str(tmp_path / "clean.db")
    rc, out, err = run(flags, path, ["build", "--db", db], root, env)
    assert rc == EXIT_OK, "[%s] a clean tree failed to build (%d)\n%s\n%s" % (
        mode, rc, out, err)
    assert "ANDON:" not in (out + err)
    assert os.path.exists(db)


@pytest.mark.parametrize("mode,flags,env", MODES, ids=MODE_IDS)
def test_the_gate_precedes_the_irreversible_step(stray, tmp_path, mode, flags,
                                                 env):
    """The guard must fire BEFORE the write, not after it. A gate that halts a
    run which has already replaced the index has stopped nothing."""
    root, path = stray
    db = str(tmp_path / "never.db")
    rc, out, err = run(flags, path, ["build", "--db", db], root, env)
    assert rc == EXIT_REFUSED
    assert not os.path.exists(db), (
        "[%s] the index was written after the ANDON fired" % mode)


def test_an_existing_index_survives_a_fired_gate(stray, tmp_path):
    """The stronger form of the same property: a build that refuses must leave
    the PREVIOUS index in place rather than removing it first and then
    halting."""
    root, path = stray
    db = str(tmp_path / "existing.db")
    with open(db, "wb") as fh:
        fh.write(b"a previous index")
    rc, out, err = run([], path, ["build", "--db", db], root)
    assert rc == EXIT_REFUSED
    with open(db, "rb") as fh:
        assert fh.read() == b"a previous index"


# ---------------------------------------------------------------------------
# the structural pin: a gate is never a bare `assert`
# ---------------------------------------------------------------------------

def andon_asserts(src):
    """Every `assert` statement whose own source carries the ANDON token."""
    tree = ast.parse(src)
    return [n for n in ast.walk(tree)
            if isinstance(n, ast.Assert)
            and "ANDON" in (ast.get_source_segment(src, n) or "")]


def test_no_module_gates_with_a_bare_assert():
    """THE STANDING LAW, pinned where it can be checked: a gate is never a bare
    `assert`, because `-O` deletes one silently."""
    offenders = []
    for name in MODULES:
        src = source_of(name)
        for n in andon_asserts(src):
            offenders.append("%s:%d" % (name, n.lineno))
    assert not offenders, (
        "%d ANDON gate(s) are still bare asserts, which -O deletes:\n  %s"
        % (len(offenders), "\n  ".join(offenders)))


def test_the_structural_check_can_fail():
    """CAN-FAIL LEG: the walk must find an ANDON assert when one exists, or its
    silence over nine modules means nothing."""
    planted = "def f(x):\n    assert x > 0, 'ANDON: planted by the can-fail leg'\n"
    assert len(andon_asserts(planted)) == 1
    assert not andon_asserts("def f(x):\n    assert x > 0, 'ordinary'\n")


def test_the_andon_exception_type_census_is_the_one_measured():
    """The exception TYPE is load-bearing, not cosmetic: `run_contract` catches
    `AssertionError` specifically and routes it to the fired-gate branch, so
    anything else would arrive as a generic runtime error with a different
    message and a different code.

    Measured 2026-08-11 against record_index 0.1.0. A change here means a gate
    was added, removed or retyped, and a report has to say which."""
    got = {}
    for name in MODULES:
        src = source_of(name)
        tree = ast.parse(src)
        per = {}
        for n in ast.walk(tree):
            if not isinstance(n, ast.Raise):
                continue
            seg = ast.get_source_segment(src, n) or ""
            if "ANDON" not in seg:
                continue
            exc = n.exc
            key = None
            if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                key = exc.func.id
            elif isinstance(exc, ast.Name):
                key = exc.id
            per[key] = per.get(key, 0) + 1
        if per:
            got[name] = per
    assert got == {"parse.py": {"AssertionError": 1}}


def test_run_contract_still_keys_on_assertionerror():
    """The other half of the pair above, and the reason it matters. If this
    handler were narrowed or renamed, the type census would be guarding
    nothing - and a fired gate would reach the operator as a runtime error."""
    src = source_of("cli.py")
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "run_contract")
    caught = [h.type.id for h in ast.walk(fn)
              if isinstance(h, ast.ExceptHandler) and isinstance(h.type, ast.Name)]
    assert "AssertionError" in caught, (
        "run_contract no longer catches AssertionError; it catches %s" % caught)
    assert caught.index("AssertionError") < caught.index("Exception"), (
        "the AssertionError handler must precede the broad one or a fired gate "
        "is reported as a runtime error: %s" % caught)


def test_the_handler_order_check_can_fail():
    """CAN-FAIL LEG for the ordering assertion above."""
    bad = ("def run_contract(fn, argv=None):\n"
           "    try:\n"
           "        return fn(argv)\n"
           "    except Exception:\n"
           "        return 2\n"
           "    except AssertionError:\n"
           "        return 4\n")
    fn = next(n for n in ast.walk(ast.parse(bad))
              if isinstance(n, ast.FunctionDef))
    caught = [h.type.id for h in ast.walk(fn)
              if isinstance(h, ast.ExceptHandler) and isinstance(h.type, ast.Name)]
    assert caught.index("AssertionError") > caught.index("Exception")


# ---------------------------------------------------------------------------
# the write surface
# ---------------------------------------------------------------------------

WRITE_MODE_CHARS = set("wax+")

#: Calls that move or destroy a file regardless of an open() mode, split by how
#: safely the name alone identifies one. THE SPLIT IS A FIRST-RUN FINDING
#: elsewhere, not a design: `replace`, `remove`, `copy` and `mkdir` all exist on
#: ordinary builtins, so the name is evidence only when the receiver is a
#: filesystem module. A guard that flags `"a/b".replace("/", "\\")` teaches its
#: readers to ignore it, and a guard people ignore is not a guard.
FS_RECEIVERS = {"os", "shutil", "pathlib", "Path", "path", "io", "codecs"}
AMBIGUOUS_ATTRS = {"remove", "rename", "replace", "rmdir", "truncate", "copy",
                   "copy2", "move", "mkdir"}
UNAMBIGUOUS_ATTRS = {"unlink", "removedirs", "copyfile", "copytree", "rmtree",
                     "write_text", "write_bytes", "touch", "makedirs"}
MUTATING_ATTRS = AMBIGUOUS_ATTRS | UNAMBIGUOUS_ATTRS
PATH_CTORS = {"Path", "PurePath", "PosixPath", "WindowsPath"}

#: The ONLY functions permitted to write. `build` writes the index, `verify`
#: writes and removes its own two determinism temporaries, `build_and_certify`
#: writes the certificate. Everything else in this package reads.
ALLOWED_WRITERS = {"build", "verify", "build_and_certify"}

#: Modules with NO file-mutating call at all. `parse.py`'s own first law is that
#: it never writes to a record: a builder that "fixes" a source document while
#: parsing it has failed, and malformed-by-convention text is a report item and
#: never an edit.
READ_ONLY_MODULES = ["__init__.py", "claims.py", "cli.py", "conventions.py",
                     "mechanism.py", "parse.py", "text.py", "vocab.py"]


def _enclosing(tree):
    owner = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for node in ast.walk(fn):
                owner.setdefault(node, fn.name)
    return owner


def _receiver(attr_node):
    """The receiver of an attribute call, as a name, or None when it is the
    result of a call whose type is unknown. Walking THROUGH a call happens only
    for a pathlib constructor: a call result is not a receiver."""
    cur = attr_node.value
    if isinstance(cur, ast.Call):
        f = cur.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
        return "Path" if name in PATH_CTORS else None
    while isinstance(cur, ast.Attribute):
        cur = cur.value
    return cur.id if isinstance(cur, ast.Name) else None


def _mode_of(node):
    mode = ""
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        mode = str(node.args[1].value)
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = str(kw.value.value)
    return mode


def scan_writes(source):
    """Every file-mutating call site: [(function, what, lineno)].

    Module level counts as the function `<module>` - a write there is worse than
    one inside a verb, not better.

    BOUND, stated rather than implied: this is a source-level guard, so a handle
    bound to a variable and written through it (`fh = io.open(p, 'w')`,
    `fh.write(x)`) is caught at the `open` and not at the `write`, and a Path
    bound to a variable and mutated through it would pass. The complement is the
    property the guard cannot be fooled about: the corpus is only ever reached
    through `Record.read`, which opens with no mode at all."""
    tree = ast.parse(source)
    owner = _enclosing(tree)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        where = owner.get(node, "<module>")
        fn = node.func
        opener = ((isinstance(fn, ast.Name) and fn.id == "open")
                  or (isinstance(fn, ast.Attribute) and fn.attr == "open"
                      and _receiver(fn) in FS_RECEIVERS))
        if opener:
            mode = _mode_of(node)
            if set(mode) & WRITE_MODE_CHARS:
                hits.append((where, "open(mode=%r)" % mode, node.lineno))
        elif isinstance(fn, ast.Attribute) and fn.attr in MUTATING_ATTRS:
            if fn.attr in UNAMBIGUOUS_ATTRS or _receiver(fn) in FS_RECEIVERS:
                hits.append((where, "%s(...)" % fn.attr, node.lineno))
    return hits


def test_only_the_three_declared_writers_write():
    bad = []
    for name in MODULES:
        for where, what, ln in scan_writes(source_of(name)):
            if where not in ALLOWED_WRITERS:
                bad.append("%s:%d in %s -> %s" % (name, ln, where, what))
    assert not bad, (
        "the package mutates files outside %s:\n  %s"
        % (sorted(ALLOWED_WRITERS), "\n  ".join(bad)))


def test_the_permitted_writers_are_actually_there():
    """An empty scan would pass the assertion above while proving nothing: the
    scanner has to be looking at what it thinks it is looking at."""
    found = set()
    for name in MODULES:
        found |= {w for w, _, _ in scan_writes(source_of(name))}
    assert found == ALLOWED_WRITERS


@pytest.mark.parametrize("name", READ_ONLY_MODULES)
def test_a_read_only_module_mutates_nothing(name):
    """`THIS FILE NEVER WRITES TO A RECORD` as a check rather than a promise."""
    assert scan_writes(source_of(name)) == []


def test_the_scanner_catches_a_corpus_write():
    """THE CAN-FAIL PROOF. Same scanner, sources that violate the property."""
    guilty = ("def parse_rulings(self):\n"
              "    with open('CLAUDE.md', 'w') as fh:\n"
              "        fh.write('fixed the heading')\n")
    hits = scan_writes(guilty)
    assert hits and hits[0][0] == "parse_rulings"

    for snippet, needle in (
            ("import io\ndef f(p):\n    io.open(p, 'w')\n", "open"),
            ("import io\ndef f(p):\n    io.open(p, mode='a')\n", "open"),
            ("import os\ndef f(a):\n    os.remove(a)\n", "remove"),
            ("import os\ndef f(a, b):\n    os.replace(a, b)\n", "replace"),
            ("import os\ndef f(a):\n    os.makedirs(a)\n", "makedirs"),
            ("import shutil\ndef f(a, b):\n    shutil.copyfile(a, b)\n", "copyfile"),
            ("import shutil\ndef f(a):\n    shutil.rmtree(a)\n", "rmtree"),
            ("from pathlib import Path\n"
             "def g(p):\n    Path(p).write_text('x')\n", "write_text"),
            ("import pathlib\n"
             "def g(p, q):\n    pathlib.Path(p).rename(q)\n", "rename"),
            ("def h(p):\n    p.unlink()\n", "unlink")):
        hits = scan_writes(snippet)
        assert any(needle in h[1] for h in hits), (
            "the scanner missed %s in:\n%s" % (needle, snippet))


def test_the_scanner_does_not_fire_on_ordinary_builtins_or_on_reads():
    """The other half. A guard that flags `"a/b".replace("/", "\\\\")` or an
    `io.open(p, encoding=...)` read teaches its readers to ignore it."""
    innocent = ("import io\n"
                "import os\n"
                "def read(p, root):\n"
                "    with io.open(p, encoding='utf-8') as fh:\n"
                "        src = fh.read()\n"
                "    q = os.path.relpath(p, root).replace('\\\\', '/')\n"
                "    seen = ['a']\n"
                "    seen.remove('a')\n"
                "    d = {}.copy()\n"
                "    with open(p, 'rb') as fh:\n"
                "        raw = fh.read()\n"
                "    return src, q, seen, d, raw\n")
    assert scan_writes(innocent) == []


def test_the_corpus_reader_opens_with_no_mode_at_all(alpha, tmp_path):
    """The property the source scan cannot be fooled about, checked at runtime:
    a record file opened for reading cannot be written through, whatever the
    scanner thinks of the call site."""
    rec = alpha.record()
    before = os.path.getmtime(os.path.join(alpha.root, "CLAUDE.md"))
    rec.read("CLAUDE.md")
    rec.lines_of("CLAUDE.md")
    rec.record_markdown()
    rec.parse_laws()
    assert os.path.getmtime(os.path.join(alpha.root, "CLAUDE.md")) == before


def test_a_whole_build_and_verify_touches_nothing_in_the_corpus(alpha, tmp_path):
    """THE END-TO-END FORM, and the one that would catch a write the AST scan's
    stated bound lets through: hash the corpus, run every verb against it, hash
    it again."""
    from conftest import tree_hashes
    before = tree_hashes(alpha.root)
    db = str(tmp_path / "x.db")
    alpha.build(db, quiet=True)
    alpha.verify(db)
    alpha.claims(db)
    assert tree_hashes(alpha.root) == before
