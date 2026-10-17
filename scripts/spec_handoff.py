#!/usr/bin/env python3
"""Generate GitHub issue drafts from accepted specs (stdlib only). Never talks to GitHub.

  python scripts/spec_handoff.py                       accepted feature specs
  python scripts/spec_handoff.py --spec FEAT-x --spec MOD-y   named accepted specs (any kind)
  python scripts/spec_handoff.py --full                always "Implement", never a delta
  python scripts/spec_handoff.py --out specs/_work/issues --root specs

Writes one <ID>.v<N>.md body per spec, in dependency order, and prints
ID<TAB>title<TAB>file<TAB>labels per issue. If git history holds an earlier version of a
spec, the issue is "Update <ID> to vN" with a delta of added/changed/retired items.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_check import KINDS, Spec, csv, dep_closure, git, load_specs  # noqa: E402

ORDER = {"domain": 0, "module": 1, "feature": 2, "decision": 3, "model": 4}


def signature(spec):
    d = {}
    for rid, _, tag, text in spec.reqs:
        d[rid] = f"{tag} {text}"
    for item in spec.invs + spec.acts + spec.ops:
        d[item["id"]] = "|".join(f"{k}={v}" for k, v in sorted(item["f"].items())) + "|" + " ".join(item["stmt"])
    return d


def previous_version(root, spec):
    rel = f"{root.name}/{KINDS[spec.kind][1]}/{spec.id}.md"
    r = git(root, "log", "--format=%H", "-n", "50", "--", rel)
    if r.returncode != 0:
        return None
    for sha in r.stdout.split():
        t = git(root, "show", f"{sha}:./{rel}")
        if t.returncode != 0:
            continue
        b = Spec(Path(rel), t.stdout)
        if b.version is not None and spec.version is not None and b.version < spec.version:
            return b
    return None


def blocking(root):
    out = {}
    p = root / "open.md"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*-\s+(OQ-\d{3})\s.*\(blocks:\s*([^)]*)\)", line)
            if m:
                for t in csv(m.group(2)):
                    out.setdefault(t, []).append(m.group(1))
    return out


def body(root, spec, by_id, prev):
    rp = lambda s: f"{root.as_posix()}/{KINDS[s.kind][1]}/{s.id}.md"  # noqa: E731
    ctx = [by_id[d] for d in dep_closure(by_id, spec.id) if d in by_id and by_id[d].kind in ("domain", "module", "feature")]
    ctx += [m for m in by_id.values() if m.kind == "module" and m.status == "accepted"
            and spec.id in m.lst("depends_on") and m not in ctx]
    ctx.sort(key=lambda s: (ORDER[s.kind], s.id))
    L = [f"<!-- spec:{spec.id} v{spec.version} -->",
         f"Spec: `{rp(spec)}` v{spec.version}. {spec.fm.get('summary', '')}", "",
         f"Read in this order: `{root.as_posix()}/index.md`, `{root.as_posix()}/glossary.md`, then"]
    L += [f"- `{rp(s)}`" for s in ctx] + [f"- `{rp(spec)}`"]
    if spec.lst("decided_by"):
        L.append(f"Rationale, only if needed: {', '.join(spec.lst('decided_by'))}")
    L.append("")
    if prev:
        cur, old = signature(spec), signature(prev)
        added = sorted(set(cur) - set(old))
        changed = sorted(k for k in cur if k in old and cur[k] != old[k])
        retired = sorted(set(spec.lst("retired")) - set(prev.lst("retired")))
        L += [f"## Delta from v{prev.version}",
              f"- Added: {', '.join(added) or 'none'}",
              f"- Changed: {', '.join(changed) or 'none'}",
              f"- Retired (remove code and tests): {', '.join(retired) or 'none'}"]
        if spec.fm.get("compat"):
            L.append(f"- Compatibility: {spec.fm['compat']}" + (" (callers must migrate; see the ADR)" if spec.fm["compat"] == "breaking" else ""))
        L.append("")
        scope_ids = set(added) | set(changed)
    else:
        scope_ids = None
    keep = lambda i: scope_ids is None or i in scope_ids  # noqa: E731
    reqs = [(r, t) for r, _, t, _ in spec.reqs if keep(r)]
    acts = [a for a in spec.acts if keep(a["id"])]
    pres = {i for a in acts for i in csv(a["f"].get("Preserves", ""))}
    invs = sorted(pres | {i["id"] for i in spec.invs if keep(i["id"])})
    L.append("## Scope")
    L += [f"- [ ] {r} [{t}]" for r, t in reqs]
    for a in acts:
        L.append(f"- [ ] {a['id']}: guard `Pre`, assert `Post`, preserves {a['f'].get('Preserves', 'nothing')}")
    for o in spec.ops:
        if keep(o["id"]):
            how = f"implements {o['f'].get('Implements', '')}" if o["f"].get("Implements") else "external: ensure Pre, handle each error"
            L.append(f"- [ ] {o['id']}: {how}")
    if spec.state and scope_ids is None:
        L.append(f"- [ ] State: {', '.join(n for n, _ in spec.state)}")
    if invs:
        L += ["", "## Invariants to protect (test, property or contract each)"]
        L += [f"- [ ] {i}" for i in invs]
    L += ["", "## Definition of done",
          "- [ ] Names in code and UI come from the glossary; no `Avoid` synonym",
          "- [ ] Code and tests mention the IDs they cover; every REQ and INV in scope has a test, every ACT code and a test",
          "- [ ] Each failing Pre returns its named error; each external error is handled as its requirement says",
          "- [ ] No spec file edited in this PR; if a spec is wrong or silent, open a spec change instead",
          "- [ ] `python scripts/spec_check.py --strict` passes",
          f"- [ ] `python scripts/spec_trace.py coverage --spec {spec.id}` (with your --src and --tests dirs) passes",
          f"- [ ] PR says: Implements {', '.join(sorted(scope_ids) if scope_ids is not None else [r for r, _ in reqs]) or spec.id}",
          "", "<!-- blocked-by -->"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Generate issue drafts from accepted specs.")
    ap.add_argument("--root", default="specs")
    ap.add_argument("--spec", action="append", default=[])
    ap.add_argument("--out", default=None)
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    root = Path(a.root)
    out = Path(a.out) if a.out else root / "_work" / "issues"
    specs = load_specs(root)
    by_id = {s.id: s for s in specs}
    blocked = blocking(root)
    picked = []
    wanted = a.spec or [s.id for s in specs if s.kind == "feature" and s.status == "accepted"]
    for sid in wanted:
        s = by_id.get(sid)
        if s is None:
            print(f"skip {sid}: no such spec", file=sys.stderr)
        elif s.status != "accepted":
            print(f"skip {sid}: status is {s.status}, only accepted specs are handed off", file=sys.stderr)
        elif any(blocked.get(i) for i in s.ids() | {s.id}):
            print(f"skip {sid}: blocked by open questions", file=sys.stderr)
        else:
            picked.append(s)
    if not picked:
        print("nothing to hand off", file=sys.stderr)
        return
    # dependency order among the picked specs
    done, ordered = set(), []

    def visit(s):
        if s.id in done:
            return
        done.add(s.id)
        for d in s.lst("depends_on"):
            if d in by_id and by_id[d] in picked:
                visit(by_id[d])
        ordered.append(s)

    for s in sorted(picked, key=lambda x: (ORDER[x.kind], x.id)):
        visit(s)
    out.mkdir(parents=True, exist_ok=True)
    for s in ordered:
        prev = None if a.full else previous_version(root, s)
        verb = f"Update {s.id} to v{s.version}" if prev else f"Implement {s.id} v{s.version}"
        title = f"{verb}: {s.fm.get('summary', '')}"[:120]
        path = out / f"{s.id}.v{s.version}.md"
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body(root, s, by_id, prev))
        print(f"{s.id}\t{title}\t{path.as_posix()}\tspec,{s.kind}")


if __name__ == "__main__":
    main()
