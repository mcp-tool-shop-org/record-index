"""The operator contract: exit codes, and how a failure reaches a person.

MEASURED THROUGH A SUBPROCESS BEFORE THIS SHAPE EXISTED - twenty rows, two
commands. The surface was inverted at BOTH ends against the standard registry
(2 for the user, 1 for the runtime) and THREE distinct outcome classes shared
exit 1: a mistyped flag, a failing verify leg, and a fired gate. A caller could
not tell "fix your command" from "do not trust this index".

  0  ok
  1  the operator's invocation was wrong
  2  the tool broke on something it did not expect
  3  declared and DELIBERATELY UNUSED - no verb has a partial-completion path,
     and a code is not populated by inventing a path for it to describe
  4  the tool ran correctly and is telling you not to proceed

FOUR IS ONE CODE, NOT TWO, deliberately: a failing verify and a fired ANDON both
mean the tool worked and the answer is no. Splitting 4 later is additive and
cheap; merging two codes later is not.
"""
import argparse
import os
import sqlite3
import sys
import traceback

from . import RootNotFound
from .conventions import ConventionsError
from .index import (EXIT_OK, EXIT_REFUSED, EXIT_RUNTIME, EXIT_USER,
                    survivable_stdout)
from .text import one_line

DEBUG_HELP = ("on failure, print the traceback as well as the structured error. "
              "PRESENTATION ONLY - it changes nothing about what runs, skips no "
              "gate, and no check consults it")


def prog_name():
    """The command the operator actually typed.

    Derived from argv rather than hardcoded: a source checkout says
    `facet_index.py`, an installed console script says something else. Advice
    that does not follow the runtime is wrong advice.
    """
    base = os.path.basename(sys.argv[0] or "")
    return base or "record-index"


class ContractParser(argparse.ArgumentParser):
    """argparse, with its usage-error exit moved from 2 to this contract's 1.

    ONLY `error()` is overridden. `exit()` is left alone deliberately: `--help`
    reaches the operator through `exit(0)`, and an override there would move a
    success onto a failure code.
    """

    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        raise SystemExit(EXIT_USER)


def user_error(message, hint):
    sys.stderr.write("%s: error: %s\n" % (prog_name(), message))
    sys.stderr.write("  hint: %s\n" % hint)
    return EXIT_USER


def debug_requested(argv=None):
    """Whether --debug was asked for. Read from argv rather than from parsed
    arguments, because the failures this governs include ones raised before a
    parse completes."""
    return "--debug" in (sys.argv[1:] if argv is None else list(argv))


def _report_failure(kind, exc, debug, hint):
    if debug:
        traceback.print_exc()
    sys.stderr.write(
        "%s: %s\n  message: %s\n  cause:   %s\n  hint:    %s\n"
        % (prog_name(), kind, str(exc) or exc.__class__.__name__,
           exc.__class__.__name__, hint))


def run_contract(fn, argv=None, db_env="RECORD_INDEX_DB"):
    """Run a console script's body under the exit-code contract.

    THIS WRAPS main() ITSELF, not the `__main__` guard: an installed console
    script calls the function directly, so a contract living in the `if __name__`
    block would be present in a source-tree run and ABSENT from every installed
    command.
    """
    debug = debug_requested(argv)
    try:
        return fn(argv)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.stderr.write("\n%s: interrupted\n" % prog_name())
        return EXIT_RUNTIME
    except AssertionError as exc:
        # A FIRED GATE. An ANDON is the tool WORKING; folding it into a generic
        # runtime error would hide its message and assign it the wrong code.
        _report_failure(
            "GATE_FIRED", exc, debug,
            "this is a gate refusing, not a defect in the tool. Fix what it "
            "names; there is no flag that skips it")
        return EXIT_REFUSED
    except ConventionsError as exc:
        _report_failure(
            "REFUSED", exc, debug,
            "conventions are a full declaration - state the missing field in "
            "the repo's own conventions.json. This tool ships no default for "
            "what a document MEANS")
        return EXIT_REFUSED
    except RootNotFound as exc:
        _report_failure(
            "REFUSED", exc, debug,
            "run this from inside a checkout of the record it serves, or pass "
            "--db (or set $%s) to work against an index directly" % db_env)
        return EXIT_REFUSED
    except Exception as exc:                                  # noqa: BLE001
        _report_failure(
            "RUNTIME_ERROR", exc, debug,
            "the traceback is above" if debug else
            "re-run the same command with --debug for the traceback")
        return EXIT_RUNTIME


def main(binding, argv=None, description=None):
    """The verb surface: build, verify, q, claims."""
    survivable_stdout()
    conv = binding.conv
    ap = ContractParser(
        description=description
        or "the derived SQLite+FTS5 index over the %s record" % conv.name)
    ap.add_argument("verb", choices=["build", "verify", "q", "claims"])
    ap.add_argument("term", nargs="?", default=None, help="query term for `q`")
    # DEFAULT None, RESOLVED BELOW. A default evaluated at parser construction
    # names a path that cannot exist on an installed command, and `q` then fails
    # with sqlite's "unable to open database file" rather than with anything a
    # reader could act on.
    ap.add_argument("--db", default=None,
                    help="the index to work against (default %s under the "
                         "record's root, or $%s)" % (conv.db_rel, conv.db_env))
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--table", default=None, help="restrict `q` to one table")
    ap.add_argument("--debug", action="store_true", help=DEBUG_HELP)
    args = ap.parse_args(argv)

    # PRECEDENCE: an explicit --db wins over the env var, which wins over the
    # record's own tracked index. The env var is a DB SELECTOR - it never names
    # a corpus.
    if not args.db:
        args.db = os.environ.get(conv.db_env) or binding.db_default()

    if args.verb == "build":
        binding.build(args.db)
        return EXIT_OK
    if args.verb == "verify":
        return binding.verify(args.db)
    if args.verb == "claims":
        return binding.claims(args.db)
    if not args.term:
        return user_error("q needs a term",
                          "%s q <term> [--table T] [--limit N]" % prog_name())
    con = sqlite3.connect(args.db)
    rows = binding.query(con, args.term, limit=args.limit * 6)
    n = 0
    for f, a, disp, line, tbl, r in rows:
        if args.table and tbl != args.table:
            continue
        head = "%s:%d" % (f, line)
        print("%-52s %s" % (head, a))
        if disp and disp.strip() and disp.strip() != a.strip():
            print("%-52s   - %s" % ("", one_line(disp, 150)))
        n += 1
        if n >= args.limit:
            break
    if n == 0:
        print("(no rows)")
    return EXIT_OK
