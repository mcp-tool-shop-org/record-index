"""The parsers. One per convention, all of them reading a declaration.

THIS FILE NEVER WRITES TO A RECORD. It parses by the record's own declared
conventions and reports what it could not parse. A builder that "fixes" a source
document while parsing it has failed - malformed-by-convention text is a report
item, never an edit.

WHAT CHANGED IN THE EXTRACTION, and why each change is here rather than in a
caller:

  * every value that was a fact about one repo is read from `self.conv`;
  * a DECLARED corpus that is absent is SKIPPED AND REPORTED, never raised on
    (S02 step-2 ruling, answer 5) - three parsers used to raise
    FileNotFoundError on a file list belonging to a different repo, which is how
    the extraction found out the lists were repo-specific in the first place;
  * an UNDECLARED corpus that exists is reported too, because only reporting
    both directions makes the declaration auditable;
  * ruling headers are a LIST of patterns, since the convention is plural in
    practice;
  * `experiment` is derived beside `arc` - grouping beside identity;
  * every vocabulary counts what it did not recognise.
"""
import io
import json
import os
import re

from . import text as T
from .mechanism import DEFAULT
from .vocab import (VocabReport, PROBE_ARTIFACT, PROBE_PHENOMENON,
                    PROBE_RULING_HEADER, PROBE_VERDICT)


class Record(object):
    """One record repo: its root, its declaration, its tuning, its findings."""

    def __init__(self, root, conventions, mechanism=None):
        self.root = root
        self.conv = conventions
        self.mech = mechanism or DEFAULT
        self.vocab = VocabReport()
        self.corpus_findings = []      # declared-but-absent / undeclared-but-present
        self.skipped_crossrefs = []    # per-Record, never module-level
        self.artifact_re = T.artifact_pattern(self.conv.artifact_extensions)
        self.supersede_re, self.supersede_title_re = T.supersede_patterns(
            self.conv.supersede_verbs)

    # -- reading ------------------------------------------------------------

    def path(self, rel):
        return os.path.join(self.root, rel.replace("/", os.sep))

    def exists(self, rel):
        return os.path.exists(self.path(rel))

    def read(self, rel):
        with io.open(self.path(rel), encoding="utf-8") as fh:
            return fh.read().replace("\r\n", "\n")

    def lines_of(self, rel):
        return self.read(rel).split("\n")

    def declared_files(self, rels, what):
        """Declared paths that exist. Absent ones become findings, not raises."""
        out = []
        for rel in rels:
            if self.exists(rel):
                out.append(rel)
            else:
                self.corpus_findings.append(
                    ("declared-but-absent", what, rel))
        return out

    # -- discovery ----------------------------------------------------------

    def _experiment_dir_files(self):
        d = self.path(self.conv.experiments_dir)
        if not os.path.isdir(d):
            self.corpus_findings.append(
                ("declared-but-absent", "corpora.experiments_dir",
                 self.conv.experiments_dir))
            return []
        return sorted(os.listdir(d))

    def ruling_documents(self):
        """(arc, experiment, path) for every ruling document, sorted.

        ⚑ `arc` is IDENTITY and stays stem-derived; `experiment` is GROUPING and
        is the `E\\d\\d` prefix. Measured before this was settled: keyed on the
        prefix alone, two of facet's ruling documents merge and collide on seven
        primary keys. The schema carries both rather than picking one.
        """
        out = []
        for fn in self._experiment_dir_files():
            if not self.conv.ruling_doc_re.match(fn):
                continue
            out.append((self.conv.arc_of_ruling_doc(fn),
                        self.conv.experiment_of(fn),
                        self.conv.experiments_dir + "/" + fn))
        return out

    def handoff_documents(self):
        """(arc, experiment, path) for every kickoff document, sorted."""
        out = []
        for fn in self._experiment_dir_files():
            if not self.conv.kickoff_doc_re.match(fn):
                continue
            out.append((self.conv.arc_of_kickoff_doc(fn),
                        self.conv.experiment_of(fn),
                        self.conv.experiments_dir + "/" + fn))
        return out

    def assert_no_undiscovered_handoffs(self, discovered):
        """THE INVERSE GUARD: a parsed handoff row in an UNDISCOVERED file fails.

        A discovery rule that only reports what it found cannot report what it
        missed. This asks the opposite question - does any file in the record
        carry a handoff header the glob did not reach. It RAISES rather than
        asserts: a gate deleted by `python -O` is not a gate.
        """
        known = {rel for _, _, rel in discovered}
        stray = []
        for fn in self._experiment_dir_files():
            rel = self.conv.experiments_dir + "/" + fn
            if not fn.endswith(".md") or rel in known:
                continue
            for ln in self.lines_of(rel):
                if any(h.match(ln) for h in self.conv.handoff_hdrs):
                    stray.append("%s :: %s" % (rel, ln.rstrip()[:70]))
                    break
        if stray:
            raise AssertionError(
                "ANDON: %d file(s) carry a session-handoff header that the "
                "kickoff glob (%s) does not reach, so their dispatches would be "
                "invisible to the handoffs table and to verify's counts:\n  %s"
                % (len(stray), self.conv.kickoff_doc_re.pattern,
                   "\n  ".join(stray)))

    def record_markdown(self):
        """Every markdown file of the record, by a sorted walk."""
        out = []
        for rel in self.conv.record_top_files:
            if self.exists(rel):
                out.append(rel)
            else:
                self.corpus_findings.append(
                    ("declared-but-absent", "corpora.record_top_files", rel))
        for root in self.conv.record_roots:
            base = self.path(root)
            if not os.path.isdir(base):
                self.corpus_findings.append(
                    ("declared-but-absent", "corpora.record_roots", root))
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames.sort()
                for fn in sorted(filenames):
                    if fn.endswith(".md"):
                        p = os.path.join(dirpath, fn)
                        out.append(os.path.relpath(p, self.root)
                                   .replace("\\", "/"))
        return sorted(set(out))

    def sweep_markdown(self):
        """Every markdown file the claims sweep reads. A superset of the above."""
        out = list(self.record_markdown())
        for rel in self.conv.sweep_extra_files:
            if self.exists(rel):
                out.append(rel)
        for root in self.conv.sweep_extra_dirs:
            base = self.path(root)
            if not os.path.isdir(base):
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames.sort()
                for fn in sorted(filenames):
                    if fn.endswith(".md"):
                        p = os.path.join(dirpath, fn)
                        out.append(os.path.relpath(p, self.root)
                                   .replace("\\", "/"))
        return sorted(set(out))

    # -- rulings ------------------------------------------------------------

    def _header_blocks(self, ls, patterns):
        """(match, line_no, body) for every header any pattern matches.

        Patterns are a LIST. Hits from all of them are merged and sorted by line,
        so a record whose ruling documents drifted into two header forms indexes
        both. Every pattern's contract is the same: group(1) is the number,
        group(2) is the tail.
        """
        hits = []
        for i, ln in enumerate(ls):
            for pat in patterns:
                m = pat.match(ln)
                if m:
                    hits.append((i, m))
                    break
        for k, (i, m) in enumerate(hits):
            end = hits[k + 1][0] if k + 1 < len(hits) else len(ls)
            for j in range(i + 1, end):
                if ls[j].startswith("## "):
                    end = j
                    break
            yield m, i, ls[i + 1:end]

    def _count_header_vocab(self, rel, ls, patterns):
        """Headings that LOOK numbered but no declared pattern reads.

        ⚑ This is the counter that would have caught a second record's
        `## N. RULING -` documents on their first build instead of leaving three
        of them silently at zero rows.
        """
        v = self.vocab.get("ruling headers", PROBE_RULING_HEADER)
        for i, ln in enumerate(ls):
            if not v.in_population(ln):
                continue
            if any(p.match(ln) for p in patterns):
                v.hit()
            else:
                v.miss(ln.strip()[:56], "%s:%d" % (rel, i + 1))

    def parse_rulings(self):
        rows = []
        for arc, experiment, rel in self.ruling_documents():
            ls = self.lines_of(rel)
            self._count_header_vocab(rel, ls, self.conv.ruling_hdrs)
            rows.extend(self._parse_numbered(arc, experiment, rel, ls,
                                             self.conv.ruling_hdrs,
                                             "ruling", "Ruling"))
            if self.conv.addenda_hdrs:
                rows.extend(self._parse_numbered(arc, experiment, rel, ls,
                                                 self.conv.addenda_hdrs,
                                                 "addendum",
                                                 "Post-ingest addenda"))
            if self.conv.amendment_hdrs:
                rows.extend(self._parse_amendments(arc, experiment, rel, ls))
        rows.sort(key=lambda r: (r["arc"], r["sort_num"], r["sort_letter"],
                                 r["kind"]))
        return rows

    def _parse_numbered(self, arc, experiment, rel, ls, patterns, kind, label):
        out = []
        for m, i, body in self._header_blocks(ls, patterns):
            num = m.group(1) or "1"     # a first addendum may carry no digit
            tail = m.group(2)
            title = re.sub(r"^\s*" + T.DASH + r"\s*", "", tail).strip()
            title = re.sub(r"^\(([^)]*)\)\s*" + T.DASH + r"\s*", "",
                           title).strip()
            anchor = "%s %s" % (label, num)
            subs = self._parse_subs(arc, experiment, rel, num, kind, body,
                                    i + 1, T.find_date(m.group(0)))
            # a parent must NOT re-index its sub-rulings' prose: every sub is its
            # own row, so including their text makes the parent compete with its
            # own children and dilutes bm25's length normalisation for both.
            own = _minus_sub_paragraphs(body, i + 1, subs)
            out.append(dict(
                arc=arc, experiment=experiment, number=num, parent=None,
                kind=kind,
                date=T.find_date(m.group(0)) or T.find_date("\n".join(body[:6])),
                holding=T.one_line(T.strip_md(title)) or T.one_line(T.strip_md(tail)),
                body=T.strip_md(own),
                file=rel, anchor=anchor, locator=ls[i].rstrip(), line=i + 1,
                sort_num=int(num), sort_letter="",
            ))
            out.extend(subs)
        return out

    def _parse_subs(self, arc, experiment, rel, parent_num, parent_kind, body,
                    body_start, parent_date):
        out = []
        for start, par in T.paragraphs(body, body_start):
            first = par[0]
            m = self.conv.sub_ruling_re.match(first)
            closure = None if m else self.conv.sub_closure_re.match(first)
            if not m and not closure:
                continue
            g = m or closure
            num, letter = g.group(1), g.group(2)
            if num != parent_num:
                # a lettered marker numbered for a DIFFERENT ruling is a
                # cross-reference opening a paragraph, not this ruling's own sub.
                self.skipped_crossrefs.append((rel, start + 1, first[:70]))
                continue
            title, rest = T.bold_lead_title(par)
            if title is None:
                continue
            if closure:
                suffix = "-" + g.group(3)
                number = num + letter + suffix
                anchor = "Ruling %s%s%s" % (num, letter, suffix)
                locator = "**%s%s%s" % (num, letter, suffix)
                kind = "sub-%s-closure" % parent_kind
                title = re.sub(r"^\d+[a-z]-[A-Z-]+\s*:?\s*", "", title)
            else:
                number = num + letter
                anchor = "Ruling %s%s" % (num, letter)
                locator = "**%s%s " % (num, letter)
                kind = "sub-" + parent_kind
                title = re.sub(r"^\d+[a-z]\s*" + T.DASH + r"\s*", "", title)
            out.append(dict(
                arc=arc, experiment=experiment, number=number, parent=num,
                kind=kind,
                date=(T.find_date(g.group(0)) or T.find_date(title)
                      or parent_date),
                holding=T.one_line(T.strip_md(title)),
                body=T.strip_md("\n".join(par)),
                file=rel, anchor=anchor, locator=locator, line=start + 1,
                sort_num=int(num), sort_letter=letter,
            ))
        return out

    def _parse_amendments(self, arc, experiment, rel, ls):
        out = []
        for m, i, body in self._header_blocks(ls, self.conv.amendment_hdrs):
            num = m.group(1)
            tail = m.group(2)
            author = tail.split(")")[0]
            title = tail.split(")", 1)[1] if ")" in tail else tail
            title = re.sub(r"^\s*" + T.DASH + r"\s*", "", title).strip()
            out.append(dict(
                arc=arc, experiment=experiment, number="A" + num, parent=None,
                kind="amendment", date=T.find_date(author),
                holding=T.one_line(T.strip_md(title)),
                body=T.strip_md("\n".join(body)),
                file=rel, anchor="Amendment %s" % num,
                locator="Amendment %s (" % num, line=i + 1,
                sort_num=int(num), sort_letter="",
            ))
        return out

    def classify(self, holding):
        """(verdict, authority) from the record's own capitalised marks.

        THE CAPITALS ARE THE CONVENTION AND MUST NOT BE NORMALISED AWAY. A
        verdict is what a ruling DOES and the record shouts it; the same word in
        lower case is an adjective describing an artifact. An earlier version
        upper-cased the holding first and so marked three rulings ACCEPTED that
        accept nothing. Match case-sensitively.
        """
        v = self.vocab.get("verdicts", PROBE_VERDICT)
        verdict = None
        for w in self.conv.verdicts:
            if re.search(r"\b%s\b" % w, holding):
                verdict = w
                break
        if v.in_population(holding):
            if verdict:
                v.hit()
            else:
                # the shouted verb this holding announces that no declared
                # verdict claims - named, so the reader can decide whether the
                # vocabulary is short or the sentence is not a verdict
                shouted = sorted(set(re.findall(PROBE_VERDICT, holding)))
                for tok in shouted[:2]:
                    v.miss(tok, holding[:48])
        authority = (self.conv.authority_named
                     if self.authority_hit(holding) else self.conv.authority_default)
        return verdict, authority

    def authority_hit(self, holding):
        return bool(self.conv.authority_re.search(holding))

    def link_supersessions(self, rulings):
        """Populate supersedes / superseded_by from EXPLICIT verbs only.

        A lower bound by construction: a record also corrects by narrative, which
        no pattern reads without guessing. The report states the coverage rather
        than implying completeness.
        """
        by_key = {}
        for r in rulings:
            by_key[(r["arc"], r["number"])] = r
            r["supersedes"] = []
            r["superseded_by"] = []
        for r in rulings:
            hay = r["holding"] + " \n " + r["body"][:self.mech.SUPERSEDE_BODY_SCAN]
            targets = (set(self.supersede_re.findall(hay))
                       | set(self.supersede_title_re.findall(r["holding"])))
            for t in sorted(targets):
                if t == r["number"]:
                    continue
                tgt = by_key.get((r["arc"], t))
                if tgt is None:
                    continue
                if t not in r["supersedes"]:
                    r["supersedes"].append(t)
                if r["number"] not in tgt["superseded_by"]:
                    tgt["superseded_by"].append(r["number"])
        for r in rulings:
            r["supersedes"] = ",".join(sorted(r["supersedes"])) or None
            r["superseded_by"] = ",".join(sorted(r["superseded_by"])) or None

    # -- laws ---------------------------------------------------------------

    def parse_laws(self):
        """The law corpus. Three forms, all a law book's own: bold-lead
        paragraphs, numbered role rules and bulleted constraints."""
        rows = []
        for rel in self.declared_files(self.conv.law_files, "corpora.law_files"):
            ls = self.lines_of(rel)
            heads = [(i, ln) for i, ln in enumerate(ls) if ln.startswith("## ")]
            bounds = []
            for k, (i, ln) in enumerate(heads):
                end = heads[k + 1][0] if k + 1 < len(heads) else len(ls)
                bounds.append((ln[3:].strip(), i, end))
            for section, s, e in bounds:
                for start, block in T.paragraphs(ls[s + 1:e], s + 1):
                    offset = 0
                    for par in T.list_items(block):
                        line = start + offset
                        offset += len(par)
                        first = par[0]
                        title, kind = None, None
                        if T.BOLD_LEAD.match(first):
                            title, _ = T.bold_lead_title(par)
                            kind = "law"
                        elif T.LIST_ITEM.match(first):
                            inner = "\n".join(par).split("**", 2)
                            # the bold must OPEN the item: anything between the
                            # marker and the `**` means it is mid-sentence
                            if (len(inner) >= 3
                                    and not T.LIST_ITEM.sub("", inner[0]).strip()):
                                title = inner[1]
                                kind = "rule" if T.NUM_RULE.match(first) else "law"
                        if title is None:
                            continue
                        stmt = T.one_line(T.strip_md(title))
                        if len(stmt) < self.mech.MIN_LAW_STATEMENT:
                            continue
                        body = T.strip_md("\n".join(par))
                        paid = self._paid_for_by(body)
                        rows.append(dict(
                            statement=stmt, kind=kind, section=section,
                            paid_for_by=paid, body=body, file=rel,
                            anchor="%s · %s" % (section, stmt[:60]),
                            locator=first.rstrip(), line=line + 1,
                        ))
        return rows

    def _paid_for_by(self, body):
        """Which experiments paid for a law, per the repo's declared pattern.

        ⚑ This is one of the two SILENT failures the extraction was halted over:
        a repo whose declared range does not match its own arcs gets NULL on
        every law and no error anywhere. The vocabulary counter below is what
        makes that visible - the population is a law body that mentions any
        experiment-shaped token at all.
        """
        if self.conv.paid_for_by_re is None:
            return None
        v = self.vocab.get("law paid_for_by", r"\bE\d\d\b")
        mentions = bool(re.search(r"\bE\d\d\b", body))
        paid = sorted(set(self.conv.paid_for_by_re.findall(body)))
        if mentions:
            if paid:
                v.hit()
            else:
                for tok in sorted(set(re.findall(r"\bE\d\d\b", body)))[:2]:
                    v.miss(tok, "law body")
        return ",".join(paid) or None

    # -- experiments --------------------------------------------------------

    def parse_experiments(self):
        """Experiments from the authored table, supplemented by the filesystem.

        The table is the authored source and is STALE by construction. An
        experiment present on disk but absent from the table enters with status
        `not in the README table` - a reported finding, never a silent fill.

        A repo that declares NO experiments table is not an error: the rows come
        from disk alone and the absence is reported.
        """
        rows = {}
        rel = self.conv.experiments_table
        if rel and self.exists(rel):
            for ln in self.lines_of(rel):
                m = self._exp_row_re().match(ln)
                if not m:
                    continue
                eid, question, status = m.group(1), m.group(2), m.group(3)
                rows[eid] = dict(
                    id=eid, question=T.one_line(T.strip_md(question), 400),
                    status=T.one_line(T.strip_md(status), 400),
                    verdict=self._experiment_verdict(status),
                    spec_file=None, report_file=None,
                    body=T.strip_md(question + " " + status),
                    file=rel, anchor="the experiment table · %s" % eid,
                    locator="| [%s]" % eid, line=0,
                )
        elif rel:
            self.corpus_findings.append(
                ("declared-but-absent", "corpora.experiments_table", rel))

        files = sorted(
            (f for f in self._experiment_dir_files()
             if self.conv.experiment_file_re.match(f)),
            key=lambda f: (0 if f.endswith(".md") else 1, f))
        for f in files:
            eid = self.conv.experiment_of(f) or f[:3]
            r = rows.get(eid)
            if r is None:
                rel_f = self.conv.experiments_dir + "/" + f
                head, head_line = self._first_heading(rel_f)
                r = rows[eid] = dict(
                    id=eid, question=None, status="not in the README table",
                    verdict=None, spec_file=None, report_file=None, body="",
                    file=rel_f, anchor="files on disk · %s" % eid,
                    locator=head, line=head_line,
                )
            rp = self.conv.experiments_dir + "/" + f
            if r["spec_file"] is None and self._is_spec_file(f):
                r["spec_file"] = rp
            if (r["report_file"] is None
                    and self.conv.report_file_fragment in f):
                r["report_file"] = rp
        if rel and self.exists(rel):
            for eid, r in rows.items():
                if r["locator"] == "| [%s]" % eid and r["line"] == 0:
                    for i, ln in enumerate(self.lines_of(rel)):
                        if (ln.startswith("| [%s]" % eid)
                                or ln.startswith("| %s " % eid)):
                            r["line"] = i + 1
                            r["locator"] = ln[:40].rstrip()
                            break
        return [rows[k] for k in sorted(rows)]

    def _exp_row_re(self):
        return re.compile(r"^\| \[?(E\d\d)\]?(?:\([^)]*\))? \| (.*?) \| (.*?) \|\s*$")

    def _is_spec_file(self, filename):
        """⚑ LIFTED from a function body. This was an inline alternation of one
        repo's own experiment filename fragments - `-cover-`, `-paint-`,
        `-cull-`, `-atlas-`, `-facial-` - with no constant name, so a
        parameterisation that moved only the named constants would have carried
        it into this package invisibly.

        ⚑ THE FRAGMENTS ARE PATTERNS, NOT SUBSTRINGS, and that is not a
        stylistic choice. The original alternation carried `-E\\d`, which is a
        regex and matches `E08-E3-predictions.md`. Declaring the fragments as
        literal substrings dropped it silently and moved one experiment's
        `spec_file` from `E08-E3-predictions.md` to `E08-canon-spec-proposal.md`
        - a one-row perturbation that the pre/post build diff caught and nothing
        else would have. Matching with `re.search` preserves the original
        semantics exactly.
        """
        return any(re.search(frag, filename)
                   for frag in self.conv.spec_file_fragments)

    def _experiment_verdict(self, status):
        """⚑ LIFTED. A SECOND verdict vocabulary, distinct from `verdicts` and
        previously an inline tuple inside a helper."""
        v = self.vocab.get("experiment status", r"\S")
        s = status.upper()
        for word in self.conv.experiment_status:
            if word in s:
                v.hit()
                return word
        if status.strip():
            v.miss(T.one_line(status, 40), "experiments table")
        return None

    def _first_heading(self, rel):
        ls = self.lines_of(rel)
        for i, ln in enumerate(ls):
            if ln.startswith("#"):
                return ln.rstrip(), i + 1
        for i, ln in enumerate(ls):
            if ln.strip():
                return ln.rstrip()[:60], i + 1
        return "", 1

    # -- handoffs -----------------------------------------------------------

    def parse_handoffs(self):
        rows = []
        docs = self.handoff_documents()
        self.assert_no_undiscovered_handoffs(docs)
        for arc, experiment, rel in docs:
            ls = self.lines_of(rel)
            for m, i, body in self._header_blocks(ls, self.conv.handoff_hdrs):
                num = m.group(1) or "1"
                tail = m.group(2)
                date = T.find_date(tail)
                title = tail.split(")", 1)[1] if ")" in tail else tail
                title = re.sub(r"^\s*" + T.DASH + r"\s*", "", title).strip()
                txt = "\n".join(body)
                rows.append(dict(
                    arc=arc, experiment=experiment, number=int(num), date=date,
                    outcome=T.one_line(T.strip_md(title), 300),
                    commits=",".join(sorted(set(T.COMMIT_RE.findall(txt)))) or None,
                    superseded=1 if "SUPERSEDED" in ls[i] else 0,
                    body=T.strip_md(txt),
                    file=rel, anchor="Session handoff %s (%s)" % (num, arc),
                    locator=ls[i].rstrip()[:60], line=i + 1,
                ))
        rows.sort(key=lambda r: (r["arc"], r["number"]))
        return rows

    # -- decisions ----------------------------------------------------------

    CLASS_LABEL = re.compile(r"^([A-Z][A-Z0-9 /_-]{3,44})(?=[:,.(—-]|\s+-\s)")

    def parse_decisions(self):
        """An INDEX over a profiles registry. The profile stays canonical.

        A repo that declares no profile files gets zero rows and no error - the
        conventions gate no longer forces this corpus to exist (S02 step-2
        ruling, answer 5).
        """
        rows = []
        for rel in self.declared_files(self.conv.profile_files,
                                       "corpora.profile_files"):
            prof = json.loads(self.read(rel))
            subject = prof.get("name") or os.path.basename(rel)
            lines = self.read(rel).split("\n")
            for key in sorted(prof.get("_still_suspended", {})):
                note = str(prof["_still_suspended"][key])
                rows.append(dict(
                    subject=subject, tool="_still_suspended", key=key,
                    value=T.one_line(note, 200), status=self._decision_status(note),
                    ruling=None, why=T.one_line(note, 400),
                    body=T.strip_md("%s %s" % (key, note)),
                    file=rel, anchor="%s · _still_suspended · %s" % (subject, key),
                    locator='"%s"' % key, line=_line_of(lines, '"%s"' % key),
                ))
            for tool in sorted(prof.get("tools", {})):
                block = prof["tools"][tool]
                for key in sorted(block):
                    ent = block[key]
                    if key.startswith("_"):
                        rows.append(dict(
                            subject=subject, tool=tool, key=key,
                            value=T.one_line(str(ent), 200), status="marker",
                            ruling=None, why=None,
                            body=T.strip_md("%s %s" % (key, ent)),
                            file=rel, anchor="%s · %s · %s" % (subject, tool, key),
                            locator='"%s"' % key, line=_line_of(lines, '"%s"' % key),
                        ))
                        continue
                    if not isinstance(ent, dict) or "value" not in ent:
                        continue
                    why = ent.get("why", "")
                    rows.append(dict(
                        subject=subject, tool=tool, key=key,
                        value=T.one_line(json.dumps(ent["value"],
                                                    ensure_ascii=False), 200),
                        status=self._decision_status(why),
                        ruling=ent.get("from"), why=T.one_line(why, 400),
                        body=T.strip_md("%s %s %s %s"
                                        % (key, ent["value"], why,
                                           ent.get("from", ""))),
                        file=rel, anchor="%s · %s · %s" % (subject, tool, key),
                        locator='"%s"' % key, line=_line_of(lines, '"%s"' % key),
                    ))
        return rows

    def _decision_status(self, why):
        """The entry's class, read ONLY from a capitalised label at the head.

        Anywhere ELSE in the prose the same words are narrative about the past,
        and reading them as status inverts their meaning: an earlier version
        scanned the whole string and labelled three entries UNDECIDED whose
        `why` says the opposite.
        """
        m = self.CLASS_LABEL.match(why.strip())
        if m:
            label = m.group(1).strip()
            if len(label.split()) <= 6:
                return label
        return "decided"

    # -- artifacts and phenomena -------------------------------------------

    def parse_artifacts(self, ruling_index):
        """Meshes, renders, sidecars and sheets, extracted by path shape.

        A RECORD HAS NO CONVENTION FOR THESE - they are paths in prose. So this
        is extraction, not parsing, and `provenance_ruling` is a locality
        heuristic labelled as one.
        """
        v = self.vocab.get("artifact kinds", PROBE_ARTIFACT)
        seen = {}
        for rel in self.record_markdown():
            ls = self.lines_of(rel)
            for start, par in T.paragraphs(ls, 0):
                body = "\n".join(par)
                status = None
                for name, pat in self.conv.status_words:
                    if re.search(pat, body):
                        status = name
                        break
                for m in self.artifact_re.finditer(body):
                    raw = m.group(1)
                    tok = raw.replace("\\", "/")
                    ext = tok.rsplit(".", 1)[-1] if "." in tok else ""
                    kind = self.conv.artifact_kinds.get(ext)
                    if kind is None:
                        # ⚑ the silent drop, now counted. A repo whose pipeline
                        # emits an extension its declaration does not carry sees
                        # the number and the extension, instead of a shorter
                        # table it has no way to notice.
                        v.miss("." + ext, "%s:%d" % (rel, start + 1))
                        continue
                    v.hit()
                    rec = seen.get(tok)
                    if rec is None:
                        rec = seen[tok] = dict(
                            path=tok, kind=kind, status=status, mentions=0,
                            provenance_ruling=_nearest_ruling(ruling_index, rel,
                                                              start + 1),
                            body="", file=rel,
                            anchor="first mentioned in %s" % rel,
                            locator=raw, line=start + 1,
                        )
                    rec["mentions"] += 1
                    if rec["status"] is None and status is not None:
                        rec["status"] = status
                    if len(rec["body"]) < self.mech.ARTIFACT_BODY_CAP:
                        rec["body"] = (rec["body"] + " "
                                       + T.one_line(T.strip_md(body), 400)).strip()
        return [seen[k] for k in sorted(seen)]

    def parse_phenomena(self, rulings):
        """The named measured effects.

        ALSO CONVENTIONLESS, and named with several different verbs. A
        phenomenon named without one of the declared verbs is invisible here,
        and the vocabulary counter states how often that happened rather than
        leaving it as an honest-sounding boundary nobody can size.
        """
        if not self.conv.phenomenon_markers:
            return []
        v = self.vocab.get("phenomenon markers", PROBE_PHENOMENON)
        rows = []
        for r in rulings:
            body = r["holding"] + "\n" + r["body"]
            hit = None
            for name, pat in self.conv.phenomenon_markers:
                if re.search(pat, body):
                    hit = name
                    break
            # THE RESIDUAL POPULATION: an announcement the VERDICT vocabulary
            # already claims is not a phenomenon this tool failed to recognise -
            # it is a verdict, recognised next door. Subtracting them is what
            # keeps this counter from reporting every `is ACCEPTED` as a miss.
            shouted = set(re.findall(PROBE_PHENOMENON, r["holding"]))
            residual = shouted - set(self.conv.verdicts)
            if hit:
                v.hit()
            elif residual:
                v.miss(sorted(residual)[0], r["anchor"])
            if hit is None:
                continue
            rows.append(dict(
                name=T.one_line(r["holding"], 140), marker=hit,
                statement=T.one_line(r["holding"], 300), instances=r["arc"],
                body=r["body"][:self.mech.PHENOMENON_BODY_CAP],
                file=r["file"], anchor=r["anchor"], locator=r["locator"],
                line=r["line"],
            ))
        rows.sort(key=lambda x: (x["file"], x["line"]))
        return rows

    # -- prose --------------------------------------------------------------

    def parse_prose(self, structured_files=None):
        """Every prose section no structured table already owns.

        Sections a structured table owns are skipped so a holding is not indexed
        twice under two identities. A `##` block owned by a table owns its `###`
        children too - otherwise a dispatch's task list is indexed twice and the
        two compete in the ranking.
        """
        owned_hdr = (list(self.conv.ruling_hdrs) + list(self.conv.addenda_hdrs)
                     + list(self.conv.handoff_hdrs))
        structured = set(structured_files or ())
        files = list(self.declared_files(self.conv.prose_files,
                                         "corpora.prose_files"))
        files += [rel for _, rel in self.conv.topical_ruling_files
                  if self.exists(rel)]
        files += [rel for _, _, rel in self.handoff_documents()]
        files += [f for f in self.record_markdown()
                  if f.startswith(self.conv.experiments_dir + "/")
                  and f not in files]
        rows = []
        for rel in sorted(set(files)):
            if rel in structured:
                continue
            ls = self.lines_of(rel)
            heads = [(i, m) for i, m in
                     ((i, T.SECTION_HDR.match(ln)) for i, ln in enumerate(ls)) if m]
            if not heads:
                body = T.strip_md("\n".join(ls))
                if len(body.strip()) < self.mech.MIN_PROSE_BODY:
                    continue
                head, hl = self._first_heading(rel)
                rows.append(dict(title=T.one_line(T.strip_md(head).lstrip("# "), 200),
                                 body=body, file=rel, anchor="(whole document)",
                                 locator=head, line=hl))
                continue
            owned_spans = []
            h2 = [i for i, _ in heads if ls[i].startswith("## ")]
            for k, i in enumerate(h2):
                if any(h.match(ls[i]) for h in owned_hdr):
                    owned_spans.append((i, h2[k + 1] if k + 1 < len(h2) else len(ls)))

            def is_owned(line_no):
                return any(a <= line_no < b for a, b in owned_spans)

            pre = T.strip_md("\n".join(ls[:heads[0][0]]))
            if len(pre.strip()) >= self.mech.MIN_PROSE_BODY:
                head, hl = self._first_heading(rel)
                rows.append(dict(title=T.one_line(T.strip_md(head).lstrip("# "), 200),
                                 body=pre, file=rel, anchor="(preamble)",
                                 locator=head, line=hl))
            for k, (i, m) in enumerate(heads):
                end = heads[k + 1][0] if k + 1 < len(heads) else len(ls)
                if is_owned(i):
                    continue
                title = T.strip_md(m.group(2)).strip()
                body = T.strip_md("\n".join(ls[i + 1:end]))
                if len(body.strip()) < self.mech.MIN_PROSE_BODY:
                    continue
                rows.append(dict(
                    title=T.one_line(title, 200), body=body, file=rel,
                    anchor=title[:80], locator=ls[i].rstrip()[:70], line=i + 1,
                ))
        rows.sort(key=lambda r: (r["file"], r["line"]))
        return rows

    # -- the declaration's own audit ----------------------------------------

    def audit_declaration(self):
        """Both directions: declared-but-absent, and undeclared-but-present.

        Only reporting both makes a declaration auditable. A declaration that
        can report what it named and not what it missed is the hardcoded-list
        defect wearing a different hat.
        """
        found = list(self.corpus_findings)
        declared = set(self.conv.prose_files) | set(self.conv.law_files)
        declared |= {rel for _, rel in self.conv.topical_ruling_files}
        declared |= set(self.conv.record_top_files)
        if self.conv.experiments_table:
            declared.add(self.conv.experiments_table)
        known_dirs = tuple([self.conv.experiments_dir + "/"]
                           + [d.rstrip("/") + "/" for d in self.conv.record_roots
                              if d not in (".", "")])
        for rel in self.record_markdown():
            if rel in declared:
                continue
            if rel.startswith(known_dirs):
                continue
            found.append(("undeclared-but-present", "corpora", rel))
        return found


def _minus_sub_paragraphs(body, body_start, subs):
    """The parent's own prose: the block minus every paragraph a sub owns."""
    owned = set()
    for s in subs:
        first = s["line"] - 1 - body_start
        n = len(s["body"].split("\n"))
        for k in range(first, first + n + 1):
            owned.add(k)
    return "\n".join(ln for k, ln in enumerate(body) if k not in owned)


def _nearest_ruling(ruling_index, rel, line):
    best = None
    for r in ruling_index:
        if r["file"] != rel or r["line"] > line:
            continue
        if best is None or r["line"] > best["line"]:
            best = r
    return best["anchor"] if best else None


def _line_of(lines, needle):
    for i, ln in enumerate(lines):
        if needle in ln:
            return i + 1
    return 0
