#!/usr/bin/env python3
"""Run the TLA+ models stored in specs/models/ with TLC (needs Java; stdlib only).

  python scripts/spec_model.py list                    models, what they check, staleness
  python scripts/spec_model.py fetch-tlc               download TLC (pinned, hash-checked) into the cache
  python scripts/spec_model.py extract MDL-x --out DIR write the .tla and .cfg blocks to DIR
  python scripts/spec_model.py run MDL-x [--stamp]     model-check one model
  python scripts/spec_model.py run --all [--stamp]     model-check every non-retired model

--stamp records the result in the model file: always "Last run", and on success
"verified_against" (the versions of the specs it depends on), which clears the
model-stale warning of spec_check.py.
Exit code: 0 all pass, 1 an invariant is violated, 2 tool or model error.
TLC is found via --jar, $TLA2TOOLS_JAR, <repo>/tools/tla2tools.jar or the cache.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_check import load_specs  # noqa: E402

TLC_URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.8.0/tla2tools.jar"
TLC_SHA256 = "15d103b7e5617780bcc904c0af12f1ad242e2b345c0301136c5be4588f17edac"


def cache_jar():
    base = Path(os.environ.get("SPEC_KIT_CACHE") or Path.home() / ".cache" / "spec-kit")
    return base / "tla2tools.jar"


def find_jar(root, arg):
    for c in (arg, os.environ.get("TLA2TOOLS_JAR"), root.resolve().parent / "tools" / "tla2tools.jar", cache_jar()):
        if c and Path(c).is_file():
            return Path(c)
    return None


def fetch_tlc():
    dest = cache_jar()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(TLC_URL, timeout=120) as r:
        data = r.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != TLC_SHA256:
        sys.exit(f"hash mismatch for {TLC_URL}: got {digest}")
    dest.write_bytes(data)
    print(f"TLC saved to {dest}")


def extract(spec):
    tla = re.search(r"^```tla[^\n]*\n(.*?)^```", spec.text, re.S | re.M)
    cfg = re.search(r"^```cfg[^\n]*\n(.*?)^```", spec.text, re.S | re.M)
    if not tla or not cfg:
        raise ValueError("needs a ```tla block and a ```cfg block")
    name = re.search(r"-{4,}\s*MODULE\s+(\w+)\s*-{4,}", tla.group(1))
    if not name:
        raise ValueError("the tla block has no '---- MODULE Name ----' header")
    return name.group(1), tla.group(1), cfg.group(1)


def inv_name(i):
    return i.replace("-", "_")


def run_one(spec, by_id, jar, timeout):
    """-> (state, message, trace) with state in ok / violated / error"""
    try:
        module, tla, cfg = extract(spec)
    except ValueError as e:
        return "error", str(e), ""
    listed = {n for line in re.findall(r"^\s*INVARIANTS?\s+(.*)$", cfg, re.M) for n in line.split()}
    missing = [i for i in spec.lst("checks") if inv_name(i) not in listed]
    if missing:
        return "error", f"cfg lacks INVARIANT {', '.join(inv_name(i) for i in missing)} for checks: {', '.join(missing)}", ""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / f"{module}.tla").write_text(tla, encoding="utf-8")
        (Path(tmp) / f"{module}.cfg").write_text(cfg, encoding="utf-8")
        cmd = ["java", "-XX:+UseParallelGC", "-cp", str(jar), "tlc2.TLC", "-deadlock", "-workers", "auto",
               "-config", f"{module}.cfg", f"{module}.tla"]
        try:
            r = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "error", f"TLC timed out after {timeout}s; shrink the constants in the cfg", ""
    out = r.stdout
    counts = re.search(r"(\d+) states generated, (\d+) distinct states found", out)
    distinct = counts.group(2) if counts else "?"
    if "Model checking completed. No error has been found." in out:
        return "ok", f"{distinct} distinct states, invariants hold: {', '.join(spec.lst('checks'))}", ""
    v = re.search(r"Invariant (\w+) is violated", out)
    if v:
        trace = out.split("The behavior up to this point is:", 1)[-1]
        trace = re.split(r"^\d+ states generated", trace, flags=re.M)[0]
        trace = re.sub(r"^State (\d+): <(.*?) line \d+.*>$", r"State \1: \2", trace, flags=re.M)
        return "violated", f"{v.group(1)} is violated", "\n".join(trace.strip().splitlines()[:80])
    err = "\n".join(l for l in (out + r.stderr).splitlines() if l.strip() and "JAVA_TOOL_OPTIONS" not in l)[-1200:]
    return "error", f"TLC failed (exit {r.returncode}):\n{err}", ""


def stamp(spec, state, message, by_id):
    t = spec.path.read_text(encoding="utf-8")
    line = f"- Last run: {datetime.date.today().isoformat()} TLC {state}: {message.splitlines()[0]}"
    if re.search(r"^- Last run:.*$", t, re.M):
        t = re.sub(r"^- Last run:.*$", lambda m: line, t, count=1, flags=re.M)
    else:
        t = re.sub(r"^(- Tool:.*)$", lambda m: m.group(1) + "\n" + line, t, count=1, flags=re.M)
    if state == "ok":
        deps = [(d, by_id[d].version) for d in spec.lst("depends_on") if d in by_id and by_id[d].kind != "model"]
        val = "[" + ", ".join(f'"{d}@{v}"' for d, v in deps) + "]"
        if re.search(r"^verified_against:.*$", t, re.M):
            t = re.sub(r"^verified_against:.*$", lambda m: f"verified_against: {val}", t, count=1, flags=re.M)
        else:
            t = t.replace("\n---\n", f"\nverified_against: {val}\n---\n", 1)
    with open(spec.path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(t)


def main():
    ap = argparse.ArgumentParser(description="Run TLA+ models with TLC.")
    ap.add_argument("--root", default="specs")
    ap.add_argument("--jar")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("fetch-tlc")
    e = sub.add_parser("extract")
    e.add_argument("model")
    e.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("model", nargs="?")
    r.add_argument("--all", action="store_true")
    r.add_argument("--stamp", action="store_true")
    r.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    if a.cmd == "fetch-tlc":
        return fetch_tlc()
    root = Path(a.root)
    specs = load_specs(root)
    by_id = {s.id: s for s in specs}
    models = [s for s in specs if s.kind == "model"]
    if a.cmd == "list":
        for m in models:
            va = dict(x.rpartition("@")[::2] for x in m.lst("verified_against"))
            stale = [d for d in m.lst("depends_on") if d in by_id and va.get(d) != str(by_id[d].version)]
            print(f"{m.id}\t{m.status}\tchecks {', '.join(m.lst('checks'))}\t{'STALE: ' + ', '.join(stale) if stale else 'verified'}")
        return
    if a.cmd == "extract":
        m = by_id.get(a.model)
        if not m or m.kind != "model":
            sys.exit(f"{a.model} is not a model")
        module, tla, cfg = extract(m)
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{module}.tla").write_text(tla, encoding="utf-8")
        (out / f"{module}.cfg").write_text(cfg, encoding="utf-8")
        print(f"wrote {out / (module + '.tla')} and {out / (module + '.cfg')}")
        return
    todo = [m for m in models if m.status not in ("superseded", "deprecated")] if a.all else [by_id.get(a.model)]
    if not a.all and (todo[0] is None or todo[0].kind != "model"):
        sys.exit(f"{a.model} is not a model (give an MDL id or --all)")
    if not todo:
        print("no models")
        return
    jar = find_jar(root, a.jar)
    if jar is None or not shutil.which("java"):
        print("need Java on PATH and TLC: run 'python scripts/spec_model.py fetch-tlc' or set TLA2TOOLS_JAR", file=sys.stderr)
        sys.exit(2)
    worst = 0
    for m in todo:
        state, message, trace = run_one(m, by_id, jar, a.timeout)
        print(f"{m.id}: {state.upper()} - {message}")
        if trace:
            print(trace)
        if a.stamp and state != "error":
            stamp(m, state, message, by_id)
        worst = max(worst, {"ok": 0, "violated": 1, "error": 2}[state])
    sys.exit(worst)


if __name__ == "__main__":
    main()
