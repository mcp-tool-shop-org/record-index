# Security Policy

## What record-index is, for the purposes of this policy

`record-index` is a Python library that reads a repo's own markdown files and writes a
SQLite database derived from them. It has **no runtime dependencies**, ships **no console
script**, and runs in the process of whatever adapter a consuming repo wrote for it.

That shapes the whole policy below: the attack surface is the surface of *importing this
package and pointing it at markdown on your own disk*, and this document's job is to say
exactly what it does. Every claim here was checked against the tree rather than assumed, and
the commands are given so you can re-run them.

## Supported versions

| Version | Supported |
|---------|-----------|
| `main` | Yes — the only supported state |

`0.1.0` is the extraction version; see [CHANGELOG.md](CHANGELOG.md) for what it marks and
what it deliberately does not. Nothing has been published to PyPI as of 2026-08-11.

## Reporting a vulnerability

Email: **64996768+mcp-tool-shop@users.noreply.github.com**

Include:

- Description of the vulnerability
- Steps to reproduce
- The commit sha affected
- Potential impact

### Response timeline

| Action | Target |
|--------|--------|
| Acknowledge report | 48 hours |
| Assess severity | 7 days |
| Release fix | 30 days |

## Threat model — measured, not asserted

### Data touched

- **Markdown files on local disk**, under the record root the caller's declaration resolves
  to. They are read and never written. The tool's own suite enforces the same discipline on
  itself: an autouse guard hashes both committed fixture corpora around every test and names
  any test that modified one.
- **A derived SQLite database**, at the path the declaration names or the caller passes.
  `build()` **removes and regenerates it from scratch** on every run; it holds no input that
  did not come from a markdown file already in the consuming repo.
- **A certificate**, written beside that database as `<db>.cert.json`. It carries the
  database's size and sha256, a per-file sha256 manifest of the markdown the index read, the
  verify transcript, and a UTC timestamp.
- **Two temporary databases** during `verify` leg 1, at `<db>.det_a.<pid>` and
  `<db>.det_b.<pid>`, both removed before the leg returns.

Nothing else is written. There is no cache directory, no home-directory state, no lockfile
outside the paths above.

### Data NOT touched

- **No credentials of any kind.** The package does not read, store, or transmit tokens,
  keys, or passwords, and none are present in the tree — swept across every tracked `.py`,
  `.md`, `.toml`, `.json`, `.yml`, `.ts`, `.astro`, `.mjs` and `.css` file for
  provider-prefixed keys, `github_pat_` / `ghp_`, Slack tokens, AWS access-key ids,
  private-key blocks, bearer tokens, and inline `api_key` / `password` assignments:
  **zero matches**. No `.env`, `.pem`, `.key` or credential-shaped file is tracked:
  **zero matches**.
- **No telemetry, analytics, crash reporting, or usage counting.** None is collected and
  none is sent. There is no opt-out because there is nothing to opt out of.

### Network egress — zero, and here is the measurement

The package imports **no** module capable of opening a socket.

```bash
grep -rnE "\b(socket|ssl|urllib|http|httplib|requests|httpx|aiohttp|ftplib|smtplib|poplib|imaplib|telnetlib|xmlrpc|webbrowser|subprocess|multiprocessing|ctypes)\b" record_index/
# → zero matches (2026-08-11, 10 modules, 3,038 lines)
```

The full set of modules `record_index/` imports, measured by parsing every module's import
statements rather than by reading its docstrings:

```
argparse  ast  codecs  datetime  hashlib  io  json
os  re  sqlite3  sys  traceback  unicodedata
```

All thirteen are standard library. This is not only documented — it is a **test**:
`tests/test_packaging.py::test_no_module_imports_anything_outside_the_standard_library`
walks every module's AST against that allow-list and fails on anything else, and
`test_the_runtime_dependency_list_is_empty` asserts the same property from the project
metadata. A dependency entering through the back door would spend the property the package
is sold on, so the check lives in the suite rather than in a reviewer's head.

The **suite** uses `subprocess` — `tests/test_cli.py` runs a generated adapter as a child
process to measure the exit codes that actually reach an operator. That is test code and
does not ship: `packages = ["record_index"]` distributes the package directory only.

### Permissions required

Ordinary user permissions. No elevation, no service installation, no registry or
system-settings writes, no scheduled tasks. The package needs read access to the markdown it
indexes and write access to the directory holding the database and its certificate. Python
3.11 or newer; nothing else.

### Known sharp edges, disclosed rather than claimed away

- **File operations are not sandboxed.** The record root comes from the caller's declaration
  or an explicit `root=` argument, and the database path comes from the caller, `--db`, or
  the declared environment variable. There is no allow-list of directories and no
  confinement. `build()` **deletes the database path before writing it**, so a caller that
  points `--db` at a file it cares about loses that file.
- **The database is regenerated, never migrated.** It is derived state. If your markdown is
  gone, the index is not a backup of it.
- **Declared patterns are compiled as regular expressions.** A repo's own `conventions.json`
  supplies them, so a hostile declaration could supply a pathological pattern and make a
  build slow. The declaration is a file in your own repo, at the same trust level as the
  code that reads it — but if you consume a declaration you did not write, read it first.
- **`verify.count_checks` interpolates its declared `table` and `where` into SQL.** Same
  trust boundary, stated explicitly rather than left for a reader to discover.
- **A gate that fires raises; it does not `assert`-and-hope.** `parse.py` raises
  `AssertionError` carrying `ANDON:` text where a discovery glob would silently drop a
  document, and the CLI contract reports it as `GATE_FIRED` with exit 4 and the hint that
  there is no flag which skips it. Because it is an `AssertionError`, running an adapter
  under `python -O` or with `PYTHONOPTIMIZE=1` does not delete this gate — it is a `raise`,
  not an `assert` statement — but any `assert` in *your* adapter would be deleted, which is
  the general reason gates in this house `raise`.
- **Four known defects are open and named**, three of them values hard-coded from the repo
  this was extracted from. They are reproduced and pinned in-tree as `xfail(strict=True)`
  tests, and listed in the README and on the handbook's
  [known defects](https://mcp-tool-shop-org.github.io/record-index/handbook/known-defects/)
  page. None is a security defect; all four are correctness defects disclosed on the front
  page rather than footnoted.

## Scope

In scope: the ten modules in `record_index/`, the suite in `tests/`, and the workflows in
`.github/workflows/`.

Out of scope: the adapter a consuming repo writes, that repo's `conventions.json`, and the
markdown corpus itself. Also out of scope: the static site under `site/`, which is a
dev-only surface that ships in no distribution — its npm dependency tree is not part of the
package and never reaches an installing user.
