"""The stale-claim sweep. REPORT-ONLY BY RULING, never a gate.

The diagnostic-vs-gate law is the grounds: this sweep swings on phrasing and on
document class, and neither may decide an exit code. It exits 0 whatever it
finds. Stale sites are an advisor's to rule, never a tool's to fix.

It reads the INDEX's measurements rather than re-deriving them from the record -
the index already did that derivation under the ratified verify legs, and a
second derivation here would be a second authority.
"""
import os
import re
import sqlite3

from . import text as T

ARC_RE = re.compile(r"\bE(\d\d)\b")

#: Anything count-claim-SHAPED. What this matches and no family parses is
#: reported as unparseable rather than guessed at.
#:
#: A RANGE IS ONLY A COUNT-CLAIM IF IT STARTS AT 1. `Rulings 1-30` asserts thirty
#: exist; `Rulings 21-23` names three of them and asserts nothing about the
#: total. An earlier pattern did not distinguish them and reported 35 such
#: references as unparseable - noise that would have buried the rows that matter.
CLAIM_SHAPED = re.compile(
    r"\b\d+\s+(?:rulings|amendments|addenda|handoffs|experiments)\b"
    r"|\b(?:Rulings?|Amendments?|Handoffs?|Addenda)\s+1\s*[–—-]\s*\d+"
    r"|\bE01\s*[–—-]\s*E?\d\d\b", re.IGNORECASE)


def _banner_line(rec, rel):
    for i, ln in enumerate(rec.lines_of(rel), 1):
        if rec.conv.banner_re.search(ln):
            return i
    return None


def _first_released_line(rec, rel):
    for i, ln in enumerate(rec.lines_of(rel), 1):
        if T.RELEASED_RE.match(ln):
            return i
    return None


def classify_document(rec, rel, line):
    """(class, why) for a claim at `rel:line`. Printed with every row."""
    conv = rec.conv
    if conv.bannered and rel == conv.bannered:
        b = _banner_line(rec, rel) if rec.exists(rel) else None
        if b is None:
            return "current-state", "the bannered document, no banner found"
        if line < b:
            return "current-state", "bannered document, above the banner at L%d" % b
        return "historical", "bannered document, below the banner at L%d" % b
    if conv.split_at_release and rel == conv.split_at_release:
        v = _first_released_line(rec, rel) if rec.exists(rel) else None
        if v is None:
            return "current-state", "the changelog, no released heading found"
        if line < v:
            return "current-state", "changelog, above the first release at L%d" % v
        return "historical", "changelog, inside a released entry (from L%d)" % v
    if rel in conv.current_state_extra:
        return "current-state", conv.current_state_extra[rel]
    if rel in conv.historical_extra:
        return "historical", conv.historical_extra[rel]
    if rel in conv.current_state_files or rel.startswith(conv.current_state_dirs):
        return "current-state", "on the declared current-state list"
    if rel.startswith(conv.historical_dirs):
        return "historical", "a kickoff / spec / report - states its counts as of writing"
    return "unclassified", "on neither list - reported, not assigned"


def measurements(con):
    """Every count this sweep can check, read from the index."""
    m = {}
    for kind in ("ruling", "amendment", "addendum"):
        for arc, n, mx in con.execute(
                "SELECT arc, COUNT(*), MAX(CAST(replace(number,'A','') AS INTEGER)) "
                "FROM rulings WHERE kind=? GROUP BY arc", (kind,)):
            m[(arc, kind)] = {"count": n, "max": mx}
    for arc, n, mx in con.execute(
            "SELECT arc, COUNT(*), MAX(number) FROM handoffs GROUP BY arc"):
        m[(arc, "handoff")] = {"count": n, "max": mx}
    n, mx = con.execute(
        "SELECT COUNT(*), MAX(CAST(substr(id,2) AS INTEGER)) FROM experiments"
    ).fetchone()
    m[("*", "experiment")] = {"count": n, "max": mx}
    return m


def claims(rec, db_path):
    conv = rec.conv
    con = sqlite3.connect(db_path)
    meas = measurements(con)
    con.close()
    rows, unparseable, families_seen = [], [], {}

    for rel in rec.sweep_markdown():
        # ⚑ LIFTED from a function body: this was an inline
        # `startswith("E15-")`, one repo's own self-reference exclusion with no
        # constant name. Documents that QUOTE these counts as data would
        # otherwise flag the sweep's own subject matter.
        if any(os.path.basename(rel).startswith(p)
               for p in conv.self_reference_exclude):
            continue
        for i, ln in enumerate(rec.lines_of(rel), 1):
            consumed = []
            for fam, kind, unit, rx in conv.claim_families:
                for m in rx.finditer(ln):
                    consumed.append((m.start(), m.end()))
                    families_seen.setdefault(fam, []).append("%s:%d" % (rel, i))
                    claimed = int(m.group(1))
                    if kind == "experiment":
                        arc = "*"
                    else:
                        pre = ARC_RE.findall(ln[:m.end()])
                        if pre:
                            arc = "E" + pre[-1]
                        else:
                            fn = ARC_RE.match(os.path.basename(rel))
                            arc = "E" + fn.group(1) if fn else None
                    if arc is None:
                        unparseable.append((rel, i, m.group(0),
                                            "no arc attributable on this line"))
                        continue
                    key = (arc, kind)
                    if key not in meas:
                        unparseable.append((rel, i, m.group(0),
                                            "no measurement for %s %s" % (arc, kind)))
                        continue
                    real = meas[key][unit]
                    cls, why = classify_document(rec, rel, i)
                    tail = ln[m.end():m.end() + 40]
                    amb = bool(T.AMBIGUOUS_SUFFIX.search(tail))
                    if amb:
                        verdict = "AMBIGUOUS"
                    elif claimed == real:
                        verdict = "ok"
                    elif cls == "current-state":
                        verdict = "STALE"
                    else:
                        verdict = "as-of-writing"
                    rows.append(dict(file=rel, line=i, fam=fam, arc=arc, kind=kind,
                                     unit=unit, claimed=claimed, measured=real,
                                     cls=cls, why=why, verdict=verdict,
                                     text=m.group(0).strip(),
                                     tail=tail.strip()[:34]))
            for m in CLAIM_SHAPED.finditer(ln):
                if any(s <= m.start() < e for s, e in consumed):
                    continue
                unparseable.append((rel, i, m.group(0).strip(),
                                    "count-claim-shaped; no family parses it"))

    print("=" * 78)
    print("record_index claims - the stale-claim sweep (REPORT-ONLY; always exits 0)")
    print("=" * 78)
    print("\nMeasured, from the index:")
    for (arc, kind) in sorted(meas, key=lambda k: (k[0], k[1])):
        v = meas[(arc, kind)]
        print("   %-16s %-10s count %-4s max %s" % (arc, kind, v["count"], v["max"]))

    order = {"STALE": 0, "AMBIGUOUS": 1, "ok": 2, "as-of-writing": 3}
    rows.sort(key=lambda r: (order.get(r["verdict"], 9), r["file"], r["line"]))
    print("\n%-14s %-14s %-11s %-11s %s"
          % ("verdict", "class", "claims", "measured", "file:line"))
    print("-" * 78)
    for r in rows:
        print("%-14s %-14s %-11s %-11s %s:%d"
              % (r["verdict"], r["cls"], "%s %d" % (r["unit"], r["claimed"]),
                 "%s %s" % (r["unit"], r["measured"]), r["file"], r["line"]))
        print("%-14s   %s - %s - %s" % ("", r["fam"], r["arc"], r["why"]))

    stale = [r for r in rows if r["verdict"] == "STALE"]
    amb = [r for r in rows if r["verdict"] == "AMBIGUOUS"]
    print("\n" + "-" * 78)
    print("STALE (current-state documents disagreeing with the record): %d" % len(stale))
    for r in stale:
        print("   %s:%d  claims %s %d, record has %s %d  [%s]"
              % (r["file"], r["line"], r["unit"], r["claimed"], r["unit"],
                 r["measured"], r["fam"]))
    print("\nAMBIGUOUS (a modifier makes the assertion unresolvable): %d" % len(amb))
    for r in amb:
        print("   %s:%d  \"%s %s\"  - reported, not resolved to a number"
              % (r["file"], r["line"], r["text"], r["tail"]))
    print("\nUNPARSEABLE (count-claim-shaped, no family): %d" % len(unparseable))
    for rel, i, txt, why in unparseable:
        print("   %s:%d  \"%s\"  - %s" % (rel, i, txt, why))

    print("\nPhrasing families found on the record: %d" % len(families_seen))
    for fam in sorted(families_seen):
        sites = families_seen[fam]
        print("   %-20s %2d site(s)   e.g. %s" % (fam, len(sites), sites[0]))
    missing = [f[0] for f in conv.claim_families if f[0] not in families_seen]
    if missing:
        print("   families with no site on the current record: %s" % ", ".join(missing))

    print("\nHealthy state is zero STALE rows. This verb never gates: exit 0.")
    return 0
