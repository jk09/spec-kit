#!/usr/bin/env python3
"""Separation guard: spec changes and implementation changes do not share a PR (stdlib only).

  python scripts/spec_guard.py [--base origin/main]

Fails (exit 1) when the diff against the base touches normative specs (specs/glossary.md,
specs/{domain,features,modules,decisions}/) and also touches implementation files. Tooling and
docs (specs/ other files, scripts/, .github/, .claude/, root *.md, CODEOWNERS) count as neutral.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

NORMATIVE = ("specs/glossary.md", "specs/domain/", "specs/features/", "specs/modules/", "specs/decisions/")
NEUTRAL = ("specs/", "scripts/", ".github/", ".claude/", "tests_kit/", "examples/")


def classify(paths):
    spec = [p for p in paths if p.startswith(NORMATIVE) and not p.endswith(".gitkeep")]
    impl = [p for p in paths if not p.startswith(NEUTRAL) and "/" in p or
            (("/" not in p) and not p.endswith(".md") and p not in ("LICENSE", ".gitignore", "CODEOWNERS"))]
    return spec, impl


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="origin/main")
    a = ap.parse_args()
    out = subprocess.run(["git", "diff", "--name-only", f"{a.base}...HEAD"], capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stderr.strip(), file=sys.stderr)
        sys.exit(2)
    spec, impl = classify([p for p in out.stdout.splitlines() if p])
    if spec and impl:
        print("spec changes must merge first, in their own PR. This PR touches both:")
        print("  specs: " + ", ".join(spec))
        print("  implementation: " + ", ".join(impl))
        sys.exit(1)
    print("guard ok")


if __name__ == "__main__":
    main()
