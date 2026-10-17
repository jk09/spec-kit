#!/usr/bin/env python3
"""Consistency checker for specs/ (stdlib only; conventions in specs/README.md).

  python scripts/spec_check.py                      check ./specs
  python scripts/spec_check.py --write-index        regenerate specs/index.md, then check
  python scripts/spec_check.py --strict             warnings fail too
  python scripts/spec_check.py --base origin/main   also enforce evolution rules against a git ref
  python scripts/spec_check.py --root examples/salon/specs

Exit code 1 if there is any error (or any warning with --strict).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

KINDS = {  # kind -> (id prefix, folder)
    "domain": ("DOM", "domain"),
    "feature": ("FEAT", "features"),
    "module": ("MOD", "modules"),
    "decision": ("ADR", "decisions"),
    "model": ("MDL", "models"),
}
FOLDERS = {v[1] for v in KINDS.values()}
STATUSES = {"draft", "accepted", "superseded", "deprecated"}
GLOSSARY_KINDS = {"entity", "role", "operation", "error", "ui", "module", "external", "enum", "event"}
REQ_TAGS = {"ubiq", "event", "state", "unwanted", "option", "complex"}
MAX_LINES, MAX_TOKENS, MAX_REQ_WORDS = 150, 2500, 40
BANNED = [
    "should", "may", "might", "normally", "usually", "typically", "appropriate",
    "appropriately", "etc", "and/or", "tbd", "todo", "if possible", "as needed",
    "user-friendly", "fast", "quickly", "easy", "simple", "robust", "flexible",
    "seamless", "intuitive",
]
STOP = {
    "When", "While", "If", "Where", "The", "Then", "A", "An", "Each", "Every", "No", "All",
    "For", "In", "On", "At", "Not", "Is", "It", "This", "That", "Any", "Only", "Both",
    "Either", "True", "False", "None",
}
SKIP_KEYS = {"By", "Writes", "Preserves", "Realizes", "Over", "Affected-by", "Kind", "Source", "Owner", "Tool",
             "Implements", "Sig"}
FREE_KEYS = {"Responsibility", "Errors", "Scope"}
ID_RE = re.compile(
    r"(?<![\w-])(REQ-\d{3}|INV-\d{3}|OQ-\d{3}|ADR-\d{4}"
    r"|(?:FEAT|DOM|MOD|MDL)-[a-z0-9]+(?:-[a-z0-9]+)*|(?:ACT|OP)-[A-Z][A-Za-z0-9]*)(?![\w-])"
)
REQ_RE = re.compile(r"^\s*-\s+(REQ-\d{3})\s+\[(\w+)\]\s+(.*\S)\s*$")
KEY_RE = re.compile(r"^\s*-\s+([A-Za-z][A-Za-z-]*):\s*(.*)$")


class Report:
    def __init__(self):
        self.items = []

    def error(self, path, line, code, msg):
        self.items.append(("error", str(path), line, code, msg))

    def warn(self, path, line, code, msg):
        self.items.append(("warn", str(path), line, code, msg))


# ---------------------------------------------------------------- parsing

def parse_val(v):
    v = v.strip()
    if v.startswith("["):
        inner = v[1:v.rfind("]")] if "]" in v else v[1:]
        return [x.strip().strip('"') for x in re.findall(r'"[^"]*"|[^,]+', inner) if x.strip()]
    return v.strip('"')


def split_doc(text):
    """-> (front matter dict, [(lineno, line)] of the body)"""
    lines = text.split("\n")
    fm, start = {}, 0
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                for ln in lines[1:i]:
                    m = re.match(r"^([A-Za-z_]+):\s*(.*)$", ln)
                    if m:
                        fm[m.group(1)] = parse_val(m.group(2))
                start = i + 1
                break
    return fm, [(n + 1, lines[n]) for n in range(start, len(lines))]


def clean(body):
    """drop fenced code and HTML comments; keep headings"""
    out, fence, comment = [], False, False
    for n, line in body:
        s = line.strip()
        if s.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if comment:
            if "-->" in s:
                comment = False
            continue
        if "<!--" in s:
            if "-->" not in s:
                comment = True
                continue
            line = re.sub(r"<!--.*?-->", "", line)
        out.append((n, line))
    return out


def csv(v):
    return [x.strip() for x in str(v).split(",") if x.strip()]


ERR_RE = re.compile(r"^\s*([A-Z][A-Za-z0-9]*)\s*:\s*(.+?)\s*\((REQ-\d{3}(?:\s*,\s*REQ-\d{3})*)\)\s*$")


def parse_errors(raw):
    """'Name: condition (REQ-001); ...' or 'none' -> ([(name, condition, [req ids])], [malformed parts])"""
    raw = (raw or "").strip()
    if not raw or raw.lower() == "none":
        return [], []
    entries, bad = [], []
    for part in raw.split(";"):
        if part.strip():
            m = ERR_RE.match(part)
            if m:
                entries.append((m.group(1), m.group(2), csv(m.group(3))))
            else:
                bad.append(part.strip())
    return entries, bad


def contract_map(spec):
    m = {}
    for a in spec.acts + spec.ops:
        f = a["f"]
        m[a["id"]] = {
            "sig": f.get("Sig", ""), "pre": f.get("Pre", ""), "post": f.get("Post", ""),
            "impl": f.get("Implements", ""),
            "writes": set(csv(f.get("Writes", ""))), "preserves": set(csv(f.get("Preserves", ""))),
            "errors": {e[0] for e in parse_errors(f.get("Errors", ""))[0]},
        }
    for i in spec.invs:
        m[i["id"]] = {"stmt": " ".join(i["stmt"]), "over": set(csv(i["f"].get("Over", "")))}
    return m


class Spec:
    def __init__(self, path, text):
        self.path = path
        self.text = text.replace("\r\n", "\n")
        self.fm, self.body = split_doc(self.text)
        self.lines = clean(self.body)
        self.id = str(self.fm.get("id", ""))
        self.kind = str(self.fm.get("kind", ""))
        self.status = str(self.fm.get("status", ""))
        try:
            self.version = int(self.fm.get("version", ""))
        except (TypeError, ValueError):
            self.version = None
        self.title, self.props = "", {}
        self.reqs, self.invs, self.acts, self.ops, self.state, self.bad = [], [], [], [], [], []
        self._parse_items()

    def lst(self, key):
        v = self.fm.get(key, [])
        return v if isinstance(v, list) else [v]

    def ids(self):
        return {r[0] for r in self.reqs} | {i["id"] for i in self.invs + self.acts + self.ops}

    def _parse_items(self):
        section, cur = "", None
        for n, line in self.lines:
            h = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
            if h:
                lvl, title = len(h.group(1)), h.group(2)
                if lvl == 1 and not self.title:
                    self.title = title
                elif lvl == 2:
                    section, cur = title.lower(), None
                elif lvl == 3:
                    m = re.match(r"^(ACT-[A-Za-z0-9]+|INV-\d{3}|OP-[A-Za-z0-9]+)\s*$", title)
                    if m:
                        cur = {"id": m.group(1), "line": n, "f": {}, "stmt": []}
                        {"ACT": self.acts, "INV": self.invs, "OP-": self.ops}[cur["id"][:3]].append(cur)
                    else:
                        cur = None
                        if re.match(r"^(ACT|INV|OP)-", title):
                            self.bad.append((n, f"malformed heading '{title}'"))
                continue
            r = REQ_RE.match(line)
            if r:
                self.reqs.append((r.group(1), n, r.group(2), r.group(3)))
                continue
            if re.match(r"^\s*-\s+REQ-", line):
                self.bad.append((n, "malformed requirement; expected '- REQ-nnn [tag] text'"))
                continue
            k = KEY_RE.match(line)
            if cur is not None:
                if k:
                    cur["f"][k.group(1)] = (k.group(2) or "").strip()
                elif line.strip():
                    cur["stmt"].append(line.strip())
                continue
            if section == "state":
                s = re.match(r"^\s*-\s+`([a-z_][A-Za-z0-9_]*)`\s*:", line)
                if s:
                    self.state.append((s.group(1), n))
                    continue
            if k:
                self.props[k.group(1)] = (k.group(2) or "").strip()


# ---------------------------------------------------------------- glossary

def term_regex(term):
    words = term.split()
    last = words[-1]
    forms = [last, last + "s", last + "es"]
    if last.endswith("y"):
        forms.append(last[:-1] + "ies")
    parts = [re.escape(w) for w in words[:-1]] + ["(?:" + "|".join(re.escape(f) for f in forms) + ")"]
    return re.compile(r"(?<![\w-])" + r"\s+".join(parts) + r"(?![\w-])", re.I)


def same_case(canon, got):
    if canon.endswith("y") and got.lower().endswith("ies"):
        return got.startswith(canon[:-1])
    return got.startswith(canon)


class Glossary:
    def __init__(self, path, rep):
        self.path, self.terms, self.ignore, self.rx, self.avoid_rx = path, {}, set(), {}, []
        if not path.exists():
            rep.error(path, 0, "glossary", "glossary.md is missing")
            return
        _, body = split_doc(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
        in_ignore = False
        for n, line in clean(body):
            h = re.match(r"^#{1,6}\s+(.*\S)", line)
            if h:
                in_ignore = h.group(1).strip().lower() == "ignore"
                continue
            if in_ignore:
                self.ignore |= {t for t in re.split(r"[,\s]+", line) if t}
                continue
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if set(line.strip()) <= set("|-: "):
                continue
            if len(cells) != 4:
                rep.error(path, n, "glossary", "row needs 4 cells: Term | Kind | Definition | Avoid")
                continue
            if cells[0].lower() == "term":
                continue
            term, kind, definition, avoid = cells
            if term in self.terms:
                rep.error(path, n, "glossary", f"duplicate term '{term}'")
                continue
            if kind not in GLOSSARY_KINDS:
                rep.error(path, n, "glossary", f"'{term}': kind must be one of {sorted(GLOSSARY_KINDS)}")
            pascal = kind in ("operation", "error")
            pat = r"[A-Z][A-Za-z0-9]*" if pascal else r"[A-Z][A-Za-z0-9]*(?: [A-Z][A-Za-z0-9]*)*"
            if not re.fullmatch(pat, term):
                rep.error(path, n, "glossary", f"'{term}': {'PascalCase' if pascal else 'Capitalised words'} required")
            if not definition:
                rep.error(path, n, "glossary", f"'{term}': definition required")
            elif len(definition.split()) > 25:
                rep.warn(path, n, "glossary", f"'{term}': definition over 25 words")
            self.terms[term] = (kind, definition, csv(avoid), n)
        owner = {}
        lower = {t.lower(): t for t in self.terms}
        for term, (_, _, avoid, n) in self.terms.items():
            for w in avoid:
                if w.lower() in lower:
                    rep.error(path, n, "glossary", f"'{w}' is avoided for '{term}' but is itself a term")
                if w.lower() in owner and owner[w.lower()] != term:
                    rep.error(path, n, "glossary", f"'{w}' is avoided for both '{owner[w.lower()]}' and '{term}'")
                owner[w.lower()] = term
                self.avoid_rx.append((re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.I), w, term))
            self.rx[term] = term_regex(term)

    def check_text(self, rep, path, n, text, case, terms, avoid_level):
        t = re.sub(r"`[^`]*`", " ", ID_RE.sub(" ", text))
        for rx, w, term in self.avoid_rx:
            if rx.search(t):
                (rep.error if avoid_level == "error" else rep.warn)(
                    path, n, "avoid-term", f"'{w}' is banned; use '{term}'")
        if not terms:
            return
        spans = []
        for canon, rx in self.rx.items():
            for m in rx.finditer(t):
                spans.append((m.start(), m.end(), canon, m.group(0)))
        spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
        kept, end = [], -1
        for sp in spans:
            if sp[0] >= end:
                kept.append(sp)
                end = sp[1]
        masked = list(t)
        for st, en, canon, got in kept:
            if case and not same_case(canon, got):
                rep.warn(path, n, "term-case", f"write '{canon}' capitalised (found '{got}')")
            for i in range(st, en):
                masked[i] = " "
        masked = "".join(masked)
        for m in re.finditer(r"(?<![\w'-])[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)*(?![\w-])", masked):
            tok = m.group(0)
            before = masked[:m.start()].rstrip()
            if not before or before[-1] in ".?!" or tok in STOP or tok in self.ignore:
                continue
            rep.warn(path, n, "unknown-term", f"'{tok}' is not in the glossary (add it or lowercase it)")


# ---------------------------------------------------------------- checks

def check_header(rep, s):
    p = s.path
    for k in ("id", "kind", "status", "version", "summary"):
        if not str(s.fm.get(k, "")).strip():
            rep.error(p, 1, "front-matter", f"missing '{k}'")
    if s.kind not in KINDS:
        rep.error(p, 1, "front-matter", f"kind must be one of {list(KINDS)}")
        return
    prefix, folder = KINDS[s.kind]
    if p.parent.name != folder:
        rep.error(p, 1, "layout", f"kind '{s.kind}' belongs in {folder}/")
    idpat = r"ADR-\d{4}" if prefix == "ADR" else prefix + r"-[a-z0-9]+(?:-[a-z0-9]+)*"
    if not re.fullmatch(idpat, s.id):
        rep.error(p, 1, "front-matter", f"id must match {idpat}")
    if p.stem != s.id:
        rep.error(p, 1, "layout", "file name must equal id")
    if s.status not in STATUSES:
        rep.error(p, 1, "front-matter", f"status must be one of {sorted(STATUSES)}")
    if s.version is None or s.version < 1:
        rep.error(p, 1, "front-matter", "version must be an integer >= 1")
    if len(str(s.fm.get("summary", ""))) > 110:
        rep.warn(p, 1, "summary", "summary over 110 characters")
    nlines, ntok = len(s.text.splitlines()), len(s.text) // 4
    if s.kind != "model" and (nlines > MAX_LINES or ntok > MAX_TOKENS):
        rep.warn(p, 1, "budget", f"{nlines} lines, ~{ntok} tokens (limit {MAX_LINES}/{MAX_TOKENS}); split it")
    for n, msg in s.bad:
        rep.error(p, n, "syntax", msg)


def req_shape(rep, s, rid, n, tag, text):
    p = s.path
    if tag not in REQ_TAGS:
        rep.error(p, n, "req-tag", f"{rid}: tag must be one of {sorted(REQ_TAGS)}")
        return
    words = text.split()
    first = words[0].lower().rstrip(",")
    openers = len(re.findall(r"(?:^|,\s+)(?:when|while|where|if)\s", text, re.I))
    ok = {
        "ubiq": first == "the" and openers == 0,
        "event": first == "when" and openers == 1,
        "state": first == "while" and openers == 1,
        "option": first == "where" and openers == 1,
        "unwanted": first == "if" and openers == 1 and re.search(r",\s*then\s", text, re.I) is not None,
        "complex": openers >= 2 and first in {"when", "while", "where", "if"},
    }[tag]
    if not ok:
        rep.error(p, n, "req-shape", f"{rid}: text does not match the EARS '{tag}' template")
    if len(re.findall(r"\bshall\b", text)) != 1:
        rep.error(p, n, "req-shall", f"{rid}: exactly one 'shall' required")
    for w in BANNED:
        if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", text, re.I):
            rep.error(p, n, "vague-word", f"{rid}: '{w}' is not allowed in requirements")
    if len(words) > MAX_REQ_WORDS:
        rep.warn(p, n, "req-long", f"{rid}: {len(words)} words; split the requirement")


def check_prose(rep, g, s):
    in_state = False
    for n, line in s.lines:
        h = re.match(r"^(#{1,6})\s+(.*)$", line)
        if h:
            in_state = h.group(1) == "##" and h.group(2).strip().lower() == "state"
            continue
        if not line.strip():
            continue
        case = False
        m = REQ_RE.match(line)
        if m:
            text, case = m.group(3), True
        else:
            k = KEY_RE.match(line)
            if k:
                if k.group(1) in SKIP_KEYS:
                    continue
                text, case = k.group(2), k.group(1) in FREE_KEYS
            elif in_state and re.match(r"^\s*-\s+`", line):
                text = line.split(":", 1)[1] if ":" in line else ""
            else:
                text = line
        g.check_text(rep, s.path, n, text, case, s.kind in ("domain", "feature", "module"),
                     "warn" if s.kind in ("decision", "model") else "error")
        if s.kind in ("domain", "feature", "module") and re.search(r"\b(TBD|TODO)\b", text):
            rep.error(s.path, n, "tbd", "no TBD/TODO in specs; write an open question in open.md")


def dep_closure(by_id, sid):
    out, todo = set(), [sid]
    while todo:
        cur = todo.pop()
        if cur in by_id:
            for d in by_id[cur].lst("depends_on"):
                if d not in out:
                    out.add(d)
                    todo.append(d)
    return out


def check_errors(rep, g, path, line, who, raw, reqtab, allowed=None):
    entries, bad = parse_errors(raw)
    for b in bad:
        rep.error(path, line, "errors", f"{who}: malformed error entry '{b}'; expected 'Name: condition (REQ-nnn)'")
    cited = set()
    for name, _, reqs in entries:
        if name not in g.terms or g.terms[name][0] != "error":
            rep.error(path, line, "errors", f"{who}: '{name}' is not a glossary term of kind error")
        for r in reqs:
            cited.add(r)
            if r not in reqtab:
                continue  # reported as unresolved-ref
            if reqtab[r][1] != "unwanted":
                rep.error(path, line, "errors", f"{who}: {r} is tagged '{reqtab[r][1]}'; an error cites an 'unwanted' requirement")
            elif allowed is not None and r not in allowed:
                rep.error(path, line, "errors", f"{who}: {r} must also be listed in Realizes")
    return entries, cited


def render_index(specs, oqs, all_ids):
    order = {k: i for i, k in enumerate(KINDS)}
    rows = ["| ID | Status | v | Summary | Depends on |", "|---|---|---|---|---|"]
    for s in sorted(specs, key=lambda x: (order.get(x.kind, 99), x.id)):
        rows.append(f"| {s.id} | {s.status} | {s.version} | {s.fm.get('summary', '')} | {', '.join(s.lst('depends_on'))} |")
    nxt = []
    for prefix, width in (("REQ", 3), ("INV", 3), ("ADR", 4), ("OQ", 3)):
        nums = [int(i.split("-")[1]) for i in all_ids if i.startswith(prefix + "-") and i.split("-")[1].isdigit()]
        nxt.append(f"{prefix}-{(max(nums) + 1 if nums else 1):0{width}d}")
    oq = "; ".join(f"{k} (blocks {', '.join(v[1]) or 'nothing'})" for k, v in sorted(oqs.items())) or "none"
    return "\n".join([
        "# Spec index",
        "",
        "<!-- GENERATED by scripts/spec_check.py --write-index. Do not edit. -->",
        "Load order: this file, glossary.md, then only the specs a task cites.",
        "",
        *rows,
        "",
        f"Open questions: {oq}",
        f"Next IDs: {' '.join(nxt)}",
        "",
    ])


def load_specs(root):
    specs = []
    for _, (_, folder) in KINDS.items():
        for p in sorted((root / folder).glob("*.md")):
            specs.append(Spec(p, p.read_text(encoding="utf-8")))
    return specs


def git(root, *args):
    return subprocess.run(["git", "-C", str(root.resolve().parent), *args], capture_output=True, text=True)


def check_base(rep, root, specs, defined, retired, ref):
    r = git(root, "ls-tree", "-r", "--name-only", ref, "--", root.name)
    if r.returncode != 0:
        rep.warn(root, 0, "base", f"cannot read git ref '{ref}' ({r.stderr.strip()[:80]}); evolution checks skipped")
        return
    cur = {s.id: s for s in specs}
    for rel in r.stdout.split("\n"):
        parts = rel.strip().split("/")
        if len(parts) != 3 or parts[1] not in FOLDERS or not rel.endswith(".md"):
            continue
        show = git(root, "show", f"{ref}:./{rel.strip()}")
        if show.returncode != 0:
            continue
        b = Spec(Path(rel.strip()), show.stdout)
        if b.status != "accepted" or b.kind == "model":
            continue  # models are evidence, re-stamped on every run; they are not versioned like specs
        c = cur.get(b.id)
        if c is None:
            rep.error(rel, 0, "evo-deleted", f"accepted spec {b.id} was removed; supersede or deprecate it instead")
            continue
        if c.status == "draft":
            rep.error(c.path, 1, "evo-status", f"{b.id} was accepted; it cannot go back to draft")
        body_changed = [x for _, x in b.body] != [x for _, x in c.body]
        fm_changed = any(b.fm.get(k) != c.fm.get(k) for k in set(b.fm) | set(c.fm) if k not in ("status", "version"))
        bumped = c.version is not None and b.version is not None and c.version > b.version
        if (body_changed or fm_changed) and not bumped:
            rep.error(c.path, 1, "evo-version", f"{b.id} changed but version was not bumped (base v{b.version})")
        elif bumped and c.fm.get("decided_by") == b.fm.get("decided_by"):
            rep.warn(c.path, 1, "evo-adr", f"{b.id} version bumped without a new decided_by ADR")
        if c.status == "accepted":
            bm, cm = contract_map(b), contract_map(c)
            changed = sorted(i for i in cm if i in bm and cm[i] != bm[i])
            removed = sorted(i for i in bm if i not in cm and i.startswith(("ACT-", "OP-")))
            refs_moved = c.kind == "module" and c.props.get("Kind") == "external" and b.lst("refs") != c.lst("refs")
            if changed or removed or refs_moved:
                compat = str(c.fm.get("compat", ""))
                what = ", ".join(changed + removed) or "pinned refs of an external module"
                if compat not in ("compatible", "breaking"):
                    rep.error(c.path, 1, "evo-compat", f"contract changed ({what}); declare 'compat: compatible' or 'compat: breaking'")
                elif compat == "breaking":
                    if c.fm.get("decided_by") == b.fm.get("decided_by"):
                        rep.error(c.path, 1, "evo-compat", "compat: breaking needs a new ADR in decided_by")
                else:
                    problems = [f"{i} was removed" for i in removed]
                    for i in changed:
                        x, y = bm[i], cm[i]
                        if "writes" not in x:
                            continue  # invariants: the claim is attested, not checkable here
                        if y["writes"] - x["writes"]:
                            problems.append(f"{i} writes more variables")
                        if x["preserves"] - y["preserves"]:
                            problems.append(f"{i} preserves fewer invariants")
                        if y["errors"] - x["errors"]:
                            problems.append(f"{i} adds errors {sorted(y['errors'] - x['errors'])}")
                        if x["sig"] != y["sig"]:
                            problems.append(f"{i} changes its signature")
                    for pr in problems:
                        rep.error(c.path, 1, "evo-compat", f"compat: compatible, but {pr}; mark it breaking and record an ADR")
        gone = b.ids() - c.ids() - set(defined) - set(retired)
        if gone:
            rep.error(c.path, 1, "evo-retire", f"{', '.join(sorted(gone))} removed without being listed in 'retired'")


def main():
    ap = argparse.ArgumentParser(description="Check specs/ for consistency.")
    ap.add_argument("--root", default="specs")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--write-index", action="store_true")
    ap.add_argument("--base", help="git ref to compare accepted specs against")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    root = Path(a.root)
    if not root.is_dir():
        sys.exit(f"no such directory: {root}")
    rep = Report()

    # load
    specs = load_specs(root)
    for p in root.glob("*.md"):
        if p.name not in {"README.md", "index.md", "glossary.md", "open.md"}:
            rep.warn(p, 0, "layout", "unexpected file in specs/")
    for d in root.iterdir():
        if d.is_dir() and d.name not in FOLDERS | {"_templates", "_work"}:
            rep.warn(d, 0, "layout", "unexpected folder in specs/")
    g = Glossary(root / "glossary.md", rep)
    for s in specs:
        check_header(rep, s)

    # open questions
    oqs, oq_spec = {}, None
    oq_path = root / "open.md"
    if oq_path.exists():
        oq_spec = Spec(oq_path, oq_path.read_text(encoding="utf-8"))
        for n, line in oq_spec.lines:
            m = re.match(r"^\s*-\s+(OQ-\d{3})\s+(.*\S)\s*$", line)
            if m:
                b = re.search(r"\(blocks:\s*([^)]*)\)", m.group(2))
                oqs[m.group(1)] = (n, csv(b.group(1)) if b else [])
            elif line.strip().startswith("- ") and not line.strip().startswith("- OQ-"):
                rep.error(oq_path, n, "syntax", "open.md lines look like '- OQ-nnn question (blocks: ID)'")

    # registry of defined and retired ids
    defined, owner = {}, {}

    def define(i, path, line, own):
        if i in defined:
            rep.error(path, line, "duplicate-id", f"{i} already defined in {Path(defined[i]).name}")
        else:
            defined[i] = str(path)
            owner[i] = own

    for s in specs:
        if s.id:
            define(s.id, s.path, 1, s.id)
        for rid, n, _, _ in s.reqs:
            define(rid, s.path, n, s.id)
        for item in s.invs + s.acts + s.ops:
            define(item["id"], s.path, item["line"], s.id)
    for oid, (n, _) in oqs.items():
        define(oid, oq_path, n, None)
    retired = {}
    for s in specs + ([oq_spec] if oq_spec else []):
        for r in s.lst("retired"):
            retired[r] = s.path
            if r in defined:
                rep.error(s.path, 1, "retired-in-use", f"{r} is listed as retired but is defined in {Path(defined[r]).name}")
    by_id = {s.id: s for s in specs}
    for oid, (n, blocks) in oqs.items():
        for t in blocks:
            sp = by_id.get(owner.get(t) or "")
            if sp and sp.status == "accepted":
                rep.error(oq_path, n, "blocked", f"{oid} is open and blocks {t} in accepted spec {sp.id}")

    # front matter references and status rules
    for s in specs:
        for key in ("depends_on", "supersedes", "decided_by", "checks"):
            for r in s.lst(key):
                if key == "checks":
                    if not re.fullmatch(r"INV-\d{3}", r) or r not in defined:
                        rep.error(s.path, 1, "unresolved-ref", f"checks: {r} is not a defined invariant")
                elif r not in by_id:
                    rep.error(s.path, 1, "unresolved-ref", f"{key}: {r} is not a spec")
                elif key == "decided_by" and by_id[r].kind != "decision":
                    rep.error(s.path, 1, "front-matter", f"decided_by: {r} is not an ADR")
        if s.id in s.lst("depends_on"):
            rep.error(s.path, 1, "cycle", "spec depends on itself")
        for d in s.lst("depends_on"):
            t = by_id.get(d)
            if not t:
                continue
            if s.status == "accepted" and t.status != "accepted":
                rep.error(s.path, 1, "status", f"accepted spec depends on {d} which is {t.status}")
            elif s.status == "draft" and t.status in ("superseded", "deprecated"):
                rep.error(s.path, 1, "status", f"depends on {d} which is {t.status}")
        if s.id in dep_closure(by_id, s.id):
            rep.error(s.path, 1, "cycle", "depends_on cycle")
    replaced = {r for s in specs for r in s.lst("supersedes")}
    for s in specs:
        if s.status == "superseded" and s.id not in replaced:
            rep.error(s.path, 1, "status", "superseded but no spec lists it in 'supersedes'")
        if s.id in replaced and s.status != "superseded":
            rep.error(s.path, 1, "status", "replaced by another spec; set status to superseded")

    # references inside text
    for s in specs + ([oq_spec] if oq_spec else []):
        for n, line in s.lines:
            if re.match(r"^#{1,6}\s", line):
                continue
            for m in ID_RE.finditer(line):
                i = m.group(1)
                if i in defined:
                    t = by_id.get(owner.get(i) or "")
                    if s.status == "accepted" and t and t.status in ("draft",) and t.id != s.id:
                        rep.warn(s.path, n, "accepted-refs-draft", f"accepted spec references {i} from draft {t.id}")
                elif i in retired:
                    rep.error(s.path, n, "retired-ref", f"{i} is retired")
                else:
                    rep.error(s.path, n, "unresolved-ref", f"{i} is not defined")

    # state variables
    state = {}
    for s in specs:
        for name, n in s.state:
            if name in state:
                rep.error(s.path, n, "duplicate-state", f"state variable '{name}' also declared in {state[name][0]}")
            else:
                state[name] = (s.id, n)

    # requirements
    for s in specs:
        for rid, n, tag, text in s.reqs:
            req_shape(rep, s, rid, n, tag, text)

    reqtab = {rid: (s, tag) for s in specs for rid, _, tag, _ in s.reqs}

    # actions
    acts = {}
    writers = {name: [] for name in state}
    for s in specs:
        closure = dep_closure(by_id, s.id) | {s.id}
        for act in s.acts:
            f, aid, n = act["f"], act["id"], act["line"]
            acts[aid] = (s, act)
            for key in ("By", "Pre", "Post", "Writes", "Preserves", "Realizes"):
                if not f.get(key):
                    rep.error(s.path, n, "action", f"{aid}: missing '{key}'")
            op = aid[4:]
            if op not in g.terms or g.terms[op][0] != "operation":
                rep.error(s.path, n, "action", f"{aid}: '{op}' is not a glossary term of kind operation")
            for role in csv(f.get("By", "")):
                if role not in g.terms or g.terms[role][0] != "role":
                    rep.error(s.path, n, "action", f"{aid}: By '{role}' is not a glossary role")
            writes = csv(f.get("Writes", ""))
            for v in writes:
                if v not in state:
                    rep.error(s.path, n, "action", f"{aid}: Writes '{v}' is not a declared state variable")
                else:
                    writers[v].append(aid)
                    if state[v][0] not in closure:
                        rep.warn(s.path, n, "depends", f"{aid} writes '{v}' from {state[v][0]}, which is not in depends_on")
            primed = set(re.findall(r"(?<![\w'])([a-z_][A-Za-z0-9_]*)'", f.get("Post", "")))
            if set(writes) != primed:
                rep.error(s.path, n, "action",
                          f"{aid}: Writes {sorted(writes)} must equal the primed variables in Post {sorted(primed)}")
            for r in csv(f.get("Preserves", "")):
                if not re.fullmatch(r"INV-\d{3}", r):
                    rep.error(s.path, n, "action", f"{aid}: Preserves '{r}' is not an invariant id")
            realizes = csv(f.get("Realizes", ""))
            for r in realizes:
                if not re.fullmatch(r"REQ-\d{3}", r):
                    rep.error(s.path, n, "action", f"{aid}: Realizes '{r}' is not a requirement id")
            raw = f.get("Errors", "")
            if not raw:
                rep.error(s.path, n, "action", f"{aid}: missing 'Errors' (write 'none' only when Pre is true)")
            else:
                entries, cited = check_errors(rep, g, s.path, n, aid, raw, reqtab, set(realizes))
                pre_true = f.get("Pre", "").strip().lower() == "true"
                if not entries and not pre_true:
                    rep.error(s.path, n, "errors", f"{aid}: Pre is not 'true', so Errors must say what happens when it fails")
                if entries and pre_true:
                    rep.warn(s.path, n, "errors", f"{aid}: Pre is 'true' but Errors are listed; state the real Pre")
                for r in realizes:
                    if r in reqtab and reqtab[r][1] == "unwanted" and r not in cited:
                        rep.warn(s.path, n, "errors", f"{aid}: realizes unwanted {r} but no Errors entry cites it")

    # invariants: the threat sweep, mechanised
    for s in specs:
        for inv in s.invs:
            f, iid, n = inv["f"], inv["id"], inv["line"]
            over, aff = csv(f.get("Over", "")), csv(f.get("Affected-by", ""))
            if not inv["stmt"]:
                rep.error(s.path, n, "invariant", f"{iid}: statement missing")
            if not over:
                rep.error(s.path, n, "invariant", f"{iid}: Over is required")
            for v in over:
                if v not in state:
                    rep.error(s.path, n, "invariant", f"{iid}: Over '{v}' is not a declared state variable")
            expected = sorted(aid for aid, (_, act) in acts.items() if set(csv(act["f"].get("Writes", ""))) & set(over))
            missing = [x for x in expected if x not in aff]
            if missing:
                rep.error(s.path, n, "invariant",
                          f"{iid} ranges over {over}; add to Affected-by: {', '.join(missing)}")
            for x in aff:
                if x in acts and x not in expected:
                    rep.warn(s.path, n, "invariant", f"{iid}: {x} does not write any variable in Over")
            for x in expected:
                if iid not in csv(acts[x][1]["f"].get("Preserves", "")):
                    rep.error(acts[x][0].path, acts[x][1]["line"], "invariant",
                              f"{x} writes a variable {iid} ranges over; add {iid} to its Preserves")
            if not expected:
                rep.warn(s.path, n, "invariant", f"{iid}: no action writes any variable in Over (missing action?)")
    for aid, (s, act) in acts.items():
        for iid in csv(act["f"].get("Preserves", "")):
            inv = next((i for sp in specs for i in sp.invs if i["id"] == iid), None)
            if inv is None:
                rep.error(s.path, act["line"], "invariant", f"{aid}: Preserves {iid} which is not defined")
    for v, ws in writers.items():
        if not ws:
            rep.warn(root, 0, "state", f"state variable '{v}' is never written by any action")

    # module operations: the contract at the module boundary
    implemented = set()
    for s in specs:
        kind = s.props.get("Kind")
        if s.kind != "module" and s.ops:
            rep.error(s.path, s.ops[0]["line"], "op", "OP blocks belong in module specs")
        for op in s.ops:
            f, oid, n = op["f"], op["id"], op["line"]
            name = oid[3:]
            if name not in g.terms or g.terms[name][0] != "operation":
                rep.error(s.path, n, "op", f"{oid}: '{name}' is not a glossary term of kind operation")
            if not f.get("Sig"):
                rep.error(s.path, n, "op", f"{oid}: missing 'Sig'")
            if kind == "internal":
                imp = csv(f.get("Implements", ""))
                if not imp:
                    rep.error(s.path, n, "op", f"{oid}: internal operation needs 'Implements: ACT-...'")
                implemented |= set(imp)
                for k in ("Pre", "Post", "Errors"):
                    if k in f:
                        rep.error(s.path, n, "op", f"{oid}: remove '{k}'; an internal operation inherits the contract of what it Implements")
            elif kind == "external":
                for k in ("Pre", "Post", "Errors"):
                    if not f.get(k):
                        rep.error(s.path, n, "op", f"{oid}: external operation needs '{k}' (what we must ensure, what we rely on, how it fails)")
                check_errors(rep, g, s.path, n, oid, f.get("Errors", ""), reqtab)
    if any(s.kind == "module" for s in specs):
        for aid, (s, act) in acts.items():
            if aid not in implemented:
                rep.warn(s.path, act["line"], "op-missing", f"{aid} is not implemented by any module operation")

    # modules, models, refs
    for s in specs:
        if s.kind == "model":
            tool = s.props.get("Tool", "")
            for fence in (("```fizzbee",) if tool.lower() == "fizzbee" else ("```tla", "```cfg")):
                if fence not in s.text:
                    rep.error(s.path, 1, "model", f"model needs a {fence} block (Tool: {tool or 'missing'})")
            if not s.lst("checks"):
                rep.error(s.path, 1, "model", "checks: list the INV ids this model verifies")
            va = {}
            for x in s.lst("verified_against"):
                k, _, v = x.rpartition("@")
                va[k] = v
            for d in s.lst("depends_on"):
                t = by_id.get(d)
                if t and t.kind != "model" and va.get(d) != str(t.version):
                    rep.warn(s.path, 1, "model-stale",
                             f"{d} is v{t.version} but the model was verified against {va.get(d, 'nothing')}; "
                             "rerun: python scripts/spec_model.py run --stamp")
        if s.kind == "module":
            k = s.props.get("Kind")
            if k not in ("internal", "external"):
                rep.error(s.path, 1, "module", "'- Kind: internal|external' line required")
            t = g.terms.get(s.title)
            if not t or t[0] not in ("module", "external"):
                rep.error(s.path, 1, "module", f"title '{s.title}' must be a glossary term of kind module or external")
            elif (k == "external") != (t[0] == "external"):
                rep.error(s.path, 1, "module", "Kind and glossary kind disagree (external vs module)")
            if k == "external" and not s.lst("refs"):
                rep.error(s.path, 1, "module", "external module must pin its documentation in refs")
        for r in s.lst("refs"):
            loc, at, rev = r.rpartition("@")
            if not at:
                loc, rev = r, ""
                rep.warn(s.path, 1, "refs", f"'{r}' is not pinned (add @revision)")
            if "://" not in loc and not (root.resolve().parent / loc).exists():
                rep.error(s.path, 1, "refs", f"path '{loc}' not found")

    # prose: glossary terms, banned synonyms
    for s in specs:
        check_prose(rep, g, s)
    if oq_spec:
        for n, line in oq_spec.lines:
            if not line.startswith("#"):
                g.check_text(rep, oq_path, n, line, False, False, "warn")
    alltext = ID_RE.sub(" ", "\n".join(x for s in specs for _, x in s.lines))
    if specs:
        for term, (kind, _, _, n) in g.terms.items():
            used = g.rx[term].search(alltext) is not None or (kind == "operation" and (f"ACT-{term}" in defined or f"OP-{term}" in defined))
            if not used:
                rep.warn(g.path, n, "glossary", f"term '{term}' is not used by any spec; delete it")

    # index
    all_ids = set(defined) | set(retired)
    index = render_index(specs, oqs, all_ids)
    ip = root / "index.md"
    if a.write_index:
        with open(ip, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(index)
    elif not ip.exists() or ip.read_text(encoding="utf-8").replace("\r\n", "\n") != index:
        rep.error(ip, 0, "index", "index.md is out of date; run with --write-index")
    if len(index.splitlines()) > MAX_LINES:
        rep.warn(ip, 0, "budget", "index over 150 lines; group or retire specs")

    # evolution
    if a.base:
        check_base(rep, root, specs, defined, retired, a.base)

    # report
    errs = warns = 0
    for level, path, line, code, msg in sorted(rep.items, key=lambda x: (x[1], x[2] or 0)):
        try:
            path = str(Path(path).resolve().relative_to(Path.cwd()))
        except ValueError:
            pass
        print(f"{path}:{line or 1}: {level}[{code}] {msg}")
        errs += level == "error"
        warns += level == "warn"
    print(f"{len(specs)} specs, {len(defined)} ids: {errs} error(s), {warns} warning(s)")
    sys.exit(1 if errs or (a.strict and warns) else 0)


if __name__ == "__main__":
    main()
