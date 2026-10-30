# Spec kit

A platform-independent kit for keeping specifications of a coding project consistent, concise and checkable, and for handing them to Claude Code through GitHub.

- Terms: one glossary; banned synonyms are enforced.
- Notation: EARS requirements plus a small TLA+-flavoured state, action and invariant language, with Design-by-Contract fields (`Pre`, `Post`, `Writes`, `Preserves`, `Errors`, module `OP` contracts).
- Evolution: versions, ADRs, retired IDs, `compat` rules, pinned references; checked against a git base.
- Skills for Claude Code: `spec-clarify` (interview), `spec-write`, `spec-model` (TLC), `spec-handoff` (GitHub issues).
- Scripts (Python 3.8+, standard library): `spec_check.py`, `spec_model.py`, `spec_trace.py`, `spec_handoff.py`, `spec_guard.py`.
- CI: `.github/workflows/spec-check.yml`, `spec-enforce.yml`; `CODEOWNERS` for spec ownership; `PORTING.md` for other agents.

No language or framework is assumed.

## Quick start
1. Put this repository's contents (or copy `specs/`, `.claude/`, `scripts/`, `.github/`, `CLAUDE.md`) into your project root.
2. `python scripts/spec_check.py --write-index` prints `0 errors`.
3. In Claude Code: `use spec-clarify: <your rough idea>`.
4. Try the worked example: `python scripts/spec_check.py --root examples/salon/specs`.

Details: `INSTALL.md`, conventions: `specs/README.md`.
