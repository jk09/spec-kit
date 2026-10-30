#!/usr/bin/env python3
"""Language-neutral traceability and contract export for accepted specs (stdlib only).

  python scripts/spec_trace.py coverage --src src --tests tests     which contracts have no code or test
  python scripts/spec_trace.py coverage --spec FEAT-x               limit to named specs
  python scripts/spec_trace.py coverage --strict                    ignore IDs that appear only in comment lines
  python scripts/spec_trace.py coverage --declared                  tests: ID must sit on an annotation or test-declaration line
  python scripts/spec_trace.py export [--out contracts.json] [--all] machine-readable contracts

Convention (any language): code that enforces a contract mentions its ID anywhere in the file
(comment, name, annotation, string); a test that covers it mentions the ID the same way.
Required evidence, for accepted specs:
  REQ, INV                 a test mentions it
  ACT, external OP         source and a test mention it
Exit code 1 if anything is missing. This proves traceability, not that the code is correct.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_check import ID_RE, csv, load_specs, parse_errors  # noqa: E402

SKIP_DIRS = {".git", "node_modules", "dist", "build", "target", "venv", ".venv", "__pycache__", "out", "vendor"}
MAX_BYTES = 1_000_000
# a line that declares or annotates a test, in common frameworks (pytest, unittest, jest, JUnit, xUnit, Go, Rust)
DECLARATION_RE = re.compile(
    r"^\s*(@|\[|#\[)|\b(def\s+test|it\s*\(|test\s*\(|describe\s*\(|func\s+Test|fn\s+test|void\s+test|public\s+void)", re.I)
COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", ";", "<!--", "%", "rem ")


def scan(dirs, exclude, code_only=False, declared_only=False):
    hits = {}
    for d in dirs:
        base = Path(d)
        if not base.is_dir():
            print(f"warning: {d} is not a directory", file=sys.stderr)
            continue
        for p in base.rglob("*"):
            if not p.is_file() or any(part in SKIP_DIRS | set(exclude) for part in p.parts):
                continue
            try:
                if p.stat().st_size > MAX_BYTES:
                    continue
                raw = p.read_bytes()
            except OSError:
                continue
            if b"\0" in raw[:2048]:
                continue
            for line in raw.decode("utf-8", errors="ignore").splitlines():
                if code_only and line.lstrip().lower().startswith(COMMENT_PREFIXES):
                    continue
                if declared_only and not DECLARATION_RE.search(line):
                    continue
                for m in ID_RE.finditer(line):
                    hits.setdefault(m.group(1), set()).add(p.as_posix())
    return hits


def items(specs, only):
    """-> [(id, kind, spec id, needs)] for the contracts that need evidence"""
    out = []
    for s in specs:
        if s.status != "accepted" or s.kind not in ("domain", "feature", "module"):
            continue
        if only and s.id not in only:
            continue
        out += [(r[0], "requirement", s.id, ("test",)) for r in s.reqs]
        out += [(i["id"], "invariant", s.id, ("test",)) for i in s.invs]
        out += [(a["id"], "action", s.id, ("src", "test")) for a in s.acts]
        if s.props.get("Kind") == "external":
            out += [(o["id"], "operation", s.id, ("src", "test")) for o in s.ops]
    return out


def export(specs, include_all):
    data = []
    for s in specs:
        if s.kind == "model" or (s.status != "accepted" and not include_all):
            continue
        for rid, _, tag, text in s.reqs:
            data.append({"id": rid, "kind": "requirement", "spec": s.id, "tag": tag, "text": text})
        for i in s.invs:
            f = i["f"]
            data.append({"id": i["id"], "kind": "invariant", "spec": s.id, "statement": " ".join(i["stmt"]),
                         "over": csv(f.get("Over", "")), "affected_by": csv(f.get("Affected-by", ""))})
        for a in s.acts:
            f = a["f"]
            entries, _ = parse_errors(f.get("Errors", ""))
            data.append({"id": a["id"], "kind": "action", "spec": s.id, "by": csv(f.get("By", "")),
                         "pre": f.get("Pre", ""), "post": f.get("Post", ""), "writes": csv(f.get("Writes", "")),
                         "preserves": csv(f.get("Preserves", "")), "realizes": csv(f.get("Realizes", "")),
                         "errors": [{"name": n, "condition": c, "requirements": r} for n, c, r in entries]})
        for o in s.ops:
            f = o["f"]
            entries, _ = parse_errors(f.get("Errors", ""))
            data.append({"id": o["id"], "kind": "operation", "spec": s.id, "module": s.id,
                         "module_kind": s.props.get("Kind", ""), "signature": f.get("Sig", "").strip("`"),
                         "implements": csv(f.get("Implements", "")), "pre": f.get("Pre", ""), "post": f.get("Post", ""),
                         "errors": [{"name": n, "condition": c, "requirements": r} for n, c, r in entries]})
    return {"specs": [{"id": s.id, "kind": s.kind, "status": s.status, "version": s.version}
                      for s in specs if s.kind != "model" and (s.status == "accepted" or include_all)],
            "contracts": data}


def main():
    ap = argparse.ArgumentParser(description="Traceability and contract export.")
    ap.add_argument("--root", default="specs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("coverage")
    c.add_argument("--src", action="append", default=None)
    c.add_argument("--tests", action="append", default=None)
    c.add_argument("--spec", action="append", default=[])
    c.add_argument("--strict", action="store_true",
                   help="count an ID only on a non-comment line (name, annotation, string)")
    c.add_argument("--declared", action="store_true",
                   help="implies --strict; in tests an ID counts only on an annotation or test-declaration line")
    c.add_argument("--exclude", action="append", default=[], help="extra directory names to skip")
    e = sub.add_parser("export")
    e.add_argument("--out")
    e.add_argument("--all", action="store_true", help="include draft specs")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    specs = load_specs(Path(a.root))
    if a.cmd == "export":
        text = json.dumps(export(specs, a.all), indent=2, ensure_ascii=False) + "\n"
        if a.out:
            with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            print(f"wrote {a.out}")
        else:
            sys.stdout.write(text)
        return
    src = scan(a.src or ["src"], a.exclude, a.strict or a.declared)
    tests = scan(a.tests or ["tests"], a.exclude, a.strict or a.declared, a.declared)
    todo = items(specs, set(a.spec))
    if not todo:
        print("no accepted specs in scope")
        return
    missing = 0
    for iid, kind, sid, needs in todo:
        lack = [n for n in needs if iid not in (src if n == "src" else tests)]
        if lack:
            missing += 1
            print(f"MISSING {iid} ({kind}, {sid}): no {' and no '.join(lack)} mentions it")
    print(f"{len(todo)} contracts, {len(todo) - missing} traced, {missing} missing")
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
