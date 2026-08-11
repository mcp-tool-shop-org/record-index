"""cli.py - the operator contract: exit codes, and how a failure reaches a person.

MEASURED THROUGH A SUBPROCESS BEFORE THIS SHAPE EXISTED. The surface was once
inverted at BOTH ends against the standard registry (2 for the user, 1 for the
runtime) and THREE distinct outcome classes shared exit 1: a mistyped flag, a
failing verify leg, and a fired gate. A caller could not tell `fix your command`
from `do not trust this index`.

  0  ok
  1  the operator's invocation was wrong
  2  the tool broke on something it did not expect
  3  declared and DELIBERATELY UNUSED
  4  the tool ran correctly and is telling you not to proceed

HALF OF THIS FILE RUNS A SUBPROCESS, because a contract that only holds when
called in-process is not the contract an operator meets. `run_contract` wraps
main() ITSELF and not the `__main__` guard, for exactly that reason: a contract
living in the `if __name__` block would be present in a source-tree run and
ABSENT from every installed command.
"""
import os
import subprocess
import sys

import pytest

import record_index
from record_index import cli as C
from record_index.conventions import ConventionsError
from record_index.index import (EXIT_OK, EXIT_PARTIAL, EXIT_REFUSED,
                                EXIT_RUNTIME, EXIT_USER)


def run(adapter_path, args, root, flags=(), env_extra=None, timeout=300):
    env = os.environ.copy()
    env.pop("PYTHONOPTIMIZE", None)
    env.pop("ALPHA_INDEX_DB", None)
    env["PYTHONIOENCODING"] = "utf-8"
    if env_extra:
        env.update(env_extra)
    p = subprocess.run([sys.executable] + list(flags) + [adapter_path]
                       + [str(a) for a in args],
                       cwd=root, env=env, capture_output=True, timeout=timeout)
    return (p.returncode, p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


# ---------------------------------------------------------------------------
# the verb surface, in process
# ---------------------------------------------------------------------------

def test_build_exits_ok_and_writes_the_index(alpha, tmp_path, capsys):
    db = str(tmp_path / "a.db")
    assert C.main(alpha, ["build", "--db", db]) == EXIT_OK
    assert os.path.exists(db)
    assert "[build]" in capsys.readouterr().out


def test_verify_returns_the_verify_verbs_own_code(alpha, alpha_db, capsys):
    assert C.main(alpha, ["verify", "--db", alpha_db]) == EXIT_OK
    capsys.readouterr()


def test_claims_returns_zero_whatever_it_finds(alpha, alpha_db, capsys):
    assert C.main(alpha, ["claims", "--db", alpha_db]) == EXIT_OK
    assert "STALE" in capsys.readouterr().out


def test_q_prints_rows_and_exits_ok(alpha, alpha_db, capsys):
    assert C.main(alpha, ["q", "the depth pass", "--db", alpha_db]) == EXIT_OK
    out = capsys.readouterr().out
    assert "docs/experiments/E01-ruling.md" in out


def test_q_with_no_term_is_a_user_error_with_a_usage_hint(alpha, alpha_db,
                                                          capsys):
    assert C.main(alpha, ["q", "--db", alpha_db]) == EXIT_USER
    err = capsys.readouterr().err
    assert "q needs a term" in err
    assert "hint:" in err


def test_q_restricts_to_one_table_when_asked(alpha, alpha_db, capsys):
    C.main(alpha, ["q", "ruling record arc", "--db", alpha_db,
                   "--table", "laws", "--limit", "3"])
    out = capsys.readouterr().out
    assert "docs/experiments" not in out or "CLAUDE.md" in out


def test_q_says_so_rather_than_printing_nothing(alpha, alpha_db, capsys):
    C.main(alpha, ["q", "zygomorphic quinquagenarian", "--db", alpha_db])
    assert "(no rows)" in capsys.readouterr().out


def test_an_unknown_verb_is_a_user_error(alpha):
    with pytest.raises(SystemExit) as exc:
        C.main(alpha, ["frobnicate"])
    assert exc.value.code == EXIT_USER


def test_an_unknown_flag_is_a_user_error(alpha):
    with pytest.raises(SystemExit) as exc:
        C.main(alpha, ["build", "--nonsense"])
    assert exc.value.code == EXIT_USER


def test_help_reaches_the_operator_through_a_success_code(alpha):
    """ONLY `error()` is overridden. `exit()` is left alone deliberately, or an
    override there would move a success onto a failure code."""
    with pytest.raises(SystemExit) as exc:
        C.main(alpha, ["--help"])
    assert exc.value.code == 0


def test_the_help_text_names_the_repo_and_its_env_var(alpha, capsys):
    with pytest.raises(SystemExit):
        C.main(alpha, ["--help"])
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "ALPHA_INDEX_DB" in out
    assert "docs/index/alpha.db" in out


# ---------------------------------------------------------------------------
# --db precedence
# ---------------------------------------------------------------------------

def test_an_explicit_db_wins_over_the_env_var(alpha, alpha_db, tmp_path,
                                              monkeypatch, capsys):
    monkeypatch.setenv("ALPHA_INDEX_DB", str(tmp_path / "never.db"))
    assert C.main(alpha, ["q", "depth pass", "--db", alpha_db]) == EXIT_OK
    assert "(no rows)" not in capsys.readouterr().out


def test_the_env_var_wins_over_the_records_own_index(alpha, alpha_db,
                                                     monkeypatch, capsys):
    """The env var is a DB SELECTOR - it never names a corpus."""
    monkeypatch.setenv("ALPHA_INDEX_DB", alpha_db)
    assert C.main(alpha, ["q", "depth pass"]) == EXIT_OK
    assert "(no rows)" not in capsys.readouterr().out


def test_the_records_own_index_is_the_last_resort(copy_fixture, monkeypatch,
                                                  capsys):
    """A default evaluated at parser construction names a path that cannot exist
    on an installed command, and `q` then fails with sqlite's `unable to open
    database file` rather than with anything a reader could act on. Resolved at
    call time, a `--db`-less and env-less `q` finds the record's own index."""
    monkeypatch.delenv("ALPHA_INDEX_DB", raising=False)
    root = copy_fixture("alpha")
    conv = record_index.conventions.load(
        os.path.join(root, "docs", "index", "conventions.json"))
    b = record_index.Binding(root, conv)
    assert not os.path.exists(b.db_default())
    assert C.main(b, ["build"]) == EXIT_OK
    assert os.path.exists(b.db_default())
    capsys.readouterr()
    assert C.main(b, ["q", "depth pass"]) == EXIT_OK
    assert "E01-ruling.md" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# run_contract - which failure gets which code
# ---------------------------------------------------------------------------

def test_a_fired_gate_is_refused_and_named_as_a_gate(capsys):
    """An ANDON is the tool WORKING; folding it into a generic runtime error
    would hide its message and assign it the wrong code."""
    def boom(argv):
        raise AssertionError("ANDON: two files carry a stray handoff")

    assert C.run_contract(boom, []) == EXIT_REFUSED
    err = capsys.readouterr().err
    assert "GATE_FIRED" in err
    assert "ANDON: two files carry a stray handoff" in err
    assert "there is no flag that skips it" in err


def test_a_declaration_error_is_refused_and_says_where_to_fix_it(capsys):
    def boom(argv):
        raise ConventionsError("the declaration is incomplete - markers")

    assert C.run_contract(boom, []) == EXIT_REFUSED
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "full declaration" in err
    assert "ships no default" in err


def test_an_unresolved_root_is_refused_and_names_the_env_var(capsys):
    def boom(argv):
        raise record_index.RootNotFound("no record corpus is bound")

    assert C.run_contract(boom, [], db_env="ALPHA_INDEX_DB") == EXIT_REFUSED
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "$ALPHA_INDEX_DB" in err


def test_an_unexpected_exception_is_a_runtime_error_and_offers_the_traceback(
        capsys):
    def boom(argv):
        raise ValueError("something nobody predicted")

    assert C.run_contract(boom, []) == EXIT_RUNTIME
    err = capsys.readouterr().err
    assert "RUNTIME_ERROR" in err
    assert "ValueError" in err
    assert "--debug" in err


def test_an_interrupt_is_a_runtime_error_and_not_a_refusal(capsys):
    def boom(argv):
        raise KeyboardInterrupt()

    assert C.run_contract(boom, []) == EXIT_RUNTIME
    assert "interrupted" in capsys.readouterr().err


def test_a_systemexit_passes_straight_through(capsys):
    """`--help` and argparse's usage error both leave through SystemExit, and
    swallowing one here would change a code the parser already decided."""
    def boom(argv):
        raise SystemExit(EXIT_USER)

    with pytest.raises(SystemExit) as exc:
        C.run_contract(boom, [])
    assert exc.value.code == EXIT_USER


def test_the_four_classes_return_four_different_codes():
    """The discrimination that the merged surface could not make. If two of
    these collided a caller would be back to guessing."""
    def gate(argv):
        raise AssertionError("ANDON")

    def decl(argv):
        raise ConventionsError("x")

    def runtime(argv):
        raise ValueError("x")

    def ok(argv):
        return EXIT_OK

    got = [C.run_contract(f, []) for f in (ok, gate, decl, runtime)]
    assert got == [EXIT_OK, EXIT_REFUSED, EXIT_REFUSED, EXIT_RUNTIME]
    assert EXIT_REFUSED not in (EXIT_OK, EXIT_USER, EXIT_RUNTIME, EXIT_PARTIAL)


def test_debug_adds_the_traceback_and_changes_nothing_else(capsys):
    """PRESENTATION ONLY - it changes nothing about what runs, skips no gate,
    and no check consults it."""
    def boom(argv):
        raise ValueError("predictable")

    plain = C.run_contract(boom, [])
    plain_err = capsys.readouterr().err
    debug = C.run_contract(boom, ["--debug"])
    debug_err = capsys.readouterr().err
    assert plain == debug == EXIT_RUNTIME
    assert "Traceback" not in plain_err
    assert "Traceback" in debug_err


def test_debug_is_read_from_argv_and_not_from_a_parse(capsys):
    """The failures this governs include ones raised before a parse
    completes."""
    assert C.debug_requested(["build", "--debug"])
    assert not C.debug_requested(["build"])


def test_prog_name_follows_the_runtime(monkeypatch):
    """Derived from argv rather than hardcoded: a source checkout says one
    thing, an installed console script another, and advice that does not follow
    the runtime is wrong advice."""
    monkeypatch.setattr(sys, "argv", [os.path.join("a", "b", "alpha_index.py")])
    assert C.prog_name() == "alpha_index.py"
    monkeypatch.setattr(sys, "argv", [""])
    assert C.prog_name() == "record-index"


# ---------------------------------------------------------------------------
# the same contract, through a subprocess
# ---------------------------------------------------------------------------

def test_the_installed_shape_builds_verifies_and_queries(adapter, tmp_path):
    root, path = adapter("alpha")
    db = str(tmp_path / "sub.db")
    rc, out, err = run(path, ["build", "--db", db], root)
    assert rc == EXIT_OK, err
    assert "rulings" in out
    rc, out, err = run(path, ["verify", "--db", db], root)
    assert rc == EXIT_OK, out[-2000:]
    assert "VERIFY PASSED" in out
    rc, out, err = run(path, ["q", "depth pass normalization", "--db", db], root)
    assert rc == EXIT_OK, err
    assert "E01-ruling.md" in out


def test_the_second_repos_adapter_works_the_same_way(adapter, tmp_path):
    root, path = adapter("beta")
    db = str(tmp_path / "subb.db")
    assert run(path, ["build", "--db", db], root)[0] == EXIT_OK
    rc, out, _ = run(path, ["verify", "--db", db], root)
    assert rc == EXIT_OK, out[-2000:]


def test_a_mistyped_flag_exits_one_through_a_subprocess(adapter):
    root, path = adapter("alpha")
    rc, out, err = run(path, ["build", "--nonsense"], root)
    assert rc == EXIT_USER
    assert "error:" in err


def test_help_exits_zero_through_a_subprocess(adapter):
    root, path = adapter("alpha")
    rc, out, err = run(path, ["--help"], root)
    assert rc == EXIT_OK
    assert "build" in out and "verify" in out


def test_a_failing_verify_exits_refused_through_a_subprocess(adapter, tmp_path):
    """The most important signal either command produces, off the code it used
    to share with a mistyped flag."""
    import sqlite3
    root, path = adapter("alpha")
    db = str(tmp_path / "broken.db")
    assert run(path, ["build", "--db", db], root)[0] == EXIT_OK
    con = sqlite3.connect(db)
    con.execute("DELETE FROM rulings WHERE arc='E01' AND kind='ruling'")
    con.commit()
    con.close()
    rc, out, err = run(path, ["verify", "--db", db], root)
    assert rc == EXIT_REFUSED, out[-2000:]
    assert "VERIFY FAILED" in out


def test_an_unexpected_break_exits_runtime_through_a_subprocess(adapter,
                                                                copy_fixture,
                                                                tmp_path):
    """MEASURED, and pinned as measured: a `verify.count_checks` leg naming a
    file that is not on disk raises FileNotFoundError, which reaches the
    operator as RUNTIME_ERROR (2) rather than as a refusal (4). The declared
    CORPUS lists are the ones that skip and report; this list is not one of
    them."""
    import io
    import json
    root, path = adapter("alpha")
    cp = os.path.join(root, "docs", "index", "conventions.json")
    with io.open(cp, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["verify"]["count_checks"] = [
        ["a leg naming nothing", "docs/experiments/E77-absent.md",
         "^## Ruling", "rulings", "arc='E01'"]]
    with io.open(cp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    db = str(tmp_path / "cc.db")
    assert run(path, ["build", "--db", db], root)[0] == EXIT_OK
    rc, out, err = run(path, ["verify", "--db", db], root)
    assert rc == EXIT_RUNTIME, (rc, err)
    assert "RUNTIME_ERROR" in err
    assert "FileNotFoundError" in err
    assert "Traceback" not in err, "a structured report must not print a raw stack"


def test_debug_prints_a_traceback_through_a_subprocess(adapter, copy_fixture,
                                                       tmp_path):
    import io
    import json
    root, path = adapter("alpha")
    cp = os.path.join(root, "docs", "index", "conventions.json")
    with io.open(cp, encoding="utf-8") as fh:
        doc = json.load(fh)
    doc["verify"]["count_checks"] = [
        ["a leg naming nothing", "docs/experiments/E77-absent.md",
         "^## Ruling", "rulings", "arc='E01'"]]
    with io.open(cp, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
    db = str(tmp_path / "cc.db")
    run(path, ["build", "--db", db], root)
    rc, out, err = run(path, ["verify", "--db", db, "--debug"], root)
    assert rc == EXIT_RUNTIME
    assert "Traceback" in err


def test_an_installed_copy_with_no_corpus_still_answers_help(tmp_path):
    """E24's measured property: an INSTALLED copy with no corpus beside it must
    still answer `--help`, because the env var and `--db` select an INDEX and
    never a corpus. Raising at import took this down."""
    from conftest import write_adapter
    lonely = str(tmp_path / "lonely")
    os.makedirs(lonely)
    path = write_adapter(lonely)
    rc, out, err = run(path, ["--help"], lonely)
    assert rc == EXIT_OK, err
    assert "build" in out


def test_an_installed_copy_with_no_corpus_still_queries_an_explicit_db(
        adapter, tmp_path):
    """The other half of the same property: `q --db <path>` works with no
    corpus anywhere, because a db is not a corpus."""
    from conftest import write_adapter
    root, path = adapter("alpha")
    db = str(tmp_path / "made.db")
    assert run(path, ["build", "--db", db], root)[0] == EXIT_OK

    lonely = str(tmp_path / "lonely")
    os.makedirs(lonely)
    lonely_adapter = write_adapter(lonely)
    rc, out, err = run(lonely_adapter, ["q", "depth pass", "--db", db], lonely)
    assert rc == EXIT_OK, err
    assert "E01-ruling.md" in out


def test_a_corpus_verb_with_no_corpus_refuses_rather_than_breaking(tmp_path):
    """The refusal is DEFERRED to the first thing that actually needs a
    document, and when it comes it is a refusal (4) and not a crash (2)."""
    from conftest import write_adapter
    lonely = str(tmp_path / "lonely")
    os.makedirs(lonely)
    path = write_adapter(lonely)
    rc, out, err = run(path, ["build", "--db", str(tmp_path / "x.db")], lonely)
    assert rc == EXIT_REFUSED, (rc, err)
    assert "REFUSED" in err
    assert "ALPHA_INDEX_DB" in err
