"""The certificate: what verify found, written beside the index it describes.

A BUILD WITHOUT ITS VERIFY IS THE UNGATED STATE THIS EXISTS TO CLOSE. The db and
the certificate move together or not at all - measured the hard way in the repo
this came from, where `build` and `verify` were separate verbs and a fresh db
could sit beside a stale certificate indefinitely, reading as verified.

So `build_and_certify` is one verb: it builds, verifies IN-PROCESS, and writes
the certificate from that verify's own transcript and exit code. There is no
path here that writes a db without writing a certificate for it.

THE CERTIFICATE DESCRIBES ONE ARTIFACT. It carries the db's size and digest, so
a certificate found beside a DIFFERENT index is detected rather than trusted -
that check is what makes "verified" a property of the bytes present rather than
of a file having once existed.
"""
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone

from .index import EXIT_OK

CERT_SUFFIX = ".cert.json"
CERT_SCHEMA = "record-index-certificate/1"

#: DUAL-ACCEPT ON READ. The writer emits exactly one id; the reader accepts the
#: pre-extraction one too, so a certificate written before the rename keeps
#: verifying instead of turning a working index into NEVER_VERIFIED on upgrade.
CERT_SCHEMA_ACCEPTED = (CERT_SCHEMA, "facet-record-index-certificate/1")


def cert_path(db_path):
    return db_path + CERT_SUFFIX


def _digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def corpus_manifest(rec):
    """path -> sha256 for every markdown file the index reads.

    The manifest is what makes staleness measurable rather than guessed: the
    corpus digest at build time is compared with the corpus now, and what MOVED
    is named. A warning a session cannot act on is a warning it learns to
    ignore.
    """
    out = {}
    for rel in rec.record_markdown():
        p = rec.path(rel)
        if os.path.exists(p):
            out[rel] = _digest(p)
    return out


def corpus_id(manifest):
    """One digest over the whole manifest, order-independent by sorting."""
    h = hashlib.sha256()
    for rel in sorted(manifest):
        h.update(rel.encode("utf-8"))
        h.update(manifest[rel].encode("ascii"))
    return h.hexdigest()


class _Tee(object):
    """Capture verify's transcript while still printing it.

    Printing matters: a verb that swallowed its own transcript would make the
    operator read a JSON file to find out what happened.
    """

    def __init__(self, stream):
        self.stream = stream
        self.buf = []

    def write(self, s):
        self.buf.append(s)
        self.stream.write(s)

    def flush(self):
        self.stream.flush()

    def __getattr__(self, item):
        return getattr(self.stream, item)


def build_and_certify(binding, db_path, verb="build_and_certify"):
    """Build, verify in-process, and write the certificate. One verb.

    Returns the certificate document. The exit code of the verify is carried in
    `verify_exit_code` so a caller reads a persisted field rather than a shell's
    `$?` that nobody kept.
    """
    rec = binding.record()
    from .index import build as _build, verify as _verify
    _build(rec, db_path, quiet=True)

    tee = _Tee(sys.stdout)
    old = sys.stdout
    sys.stdout = tee
    try:
        rc = _verify(binding.record(), db_path)
    finally:
        sys.stdout = old
    transcript = "".join(tee.buf).split("\n")

    manifest = corpus_manifest(rec)
    doc = {
        "schema": CERT_SCHEMA,
        "written_by": "record_index.certificate",
        "repo": binding.conv.name,
        "verb": verb,
        "verified_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "state": "PASSED" if rc == EXIT_OK else "FAILED",
        "verify_exit_code": rc,
        "db": {"path": os.path.basename(db_path),
               "bytes": os.path.getsize(db_path),
               "sha256": _digest(db_path)},
        "corpus": {"files": len(manifest), "id": corpus_id(manifest),
                   "manifest": manifest},
        "transcript": transcript,
    }
    with io.open(cert_path(db_path), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return doc


def health(binding, db_path):
    """SERVING / STALE / the refusal that says why. Cheap - one small file."""
    if not os.path.exists(db_path):
        return {"state": "INDEX_MISSING", "serving": False,
                "why": "no index at %s" % db_path}
    cp = cert_path(db_path)
    if not os.path.exists(cp):
        return {"state": "INDEX_NEVER_VERIFIED", "serving": False,
                "why": "no certificate beside %s" % os.path.basename(db_path)}
    try:
        with io.open(cp, encoding="utf-8") as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict):
            raise ValueError("certificate is not an object")
        for k in ("schema", "state", "db", "corpus"):
            if k not in doc:
                raise ValueError("certificate has no %r" % k)
        if doc["schema"] not in CERT_SCHEMA_ACCEPTED:
            raise ValueError("certificate schema %r" % doc["schema"])
    except (ValueError, OSError, UnicodeDecodeError) as exc:
        return {"state": "INDEX_NEVER_VERIFIED", "serving": False,
                "why": "certificate unreadable: %s" % exc}
    if doc["state"] != "PASSED":
        return {"state": "INDEX_VERIFY_FAILED", "serving": False,
                "why": "the certificate records a failed verify"}
    if doc["db"]["sha256"] != _digest(db_path):
        return {"state": "INDEX_NEVER_VERIFIED", "serving": False,
                "why": "the certificate describes a different index"}
    live = corpus_manifest(binding.record())
    if corpus_id(live) != doc["corpus"]["id"]:
        moved = sorted(set(live) ^ set(doc["corpus"]["manifest"]))
        changed = [r for r in set(live) & set(doc["corpus"]["manifest"])
                   if live[r] != doc["corpus"]["manifest"][r]]
        # STALE WARNS RATHER THAN REFUSES, on purpose: the db commits at session
        # boundaries, not every fold, so bounded staleness is the ruled normal
        # state of a fresh clone and a refusal here would fire on correct work.
        return {"state": "STALE", "serving": True,
                "why": "the corpus moved since this index was built",
                "moved": sorted(moved + changed)[:12],
                "moved_total": len(moved) + len(changed)}
    return {"state": "SERVING", "serving": True, "why": None}
