# Spec kit: install

Contents mirror a repo root.

| Path | Purpose |
|---|---|
| `specs/` | conventions (`README.md`), empty glossary/index/open list, templates |
| `.claude/skills/` | `spec-clarify`, `spec-write`, `spec-model`, `spec-handoff` for Claude Code |
| `scripts/spec_check.py` | consistency checker (Python 3.8+, standard library only) |
| `scripts/spec_model.py` | runs TLA+ models with TLC (needs Java 11+) |
| `scripts/spec_trace.py` | traceability: contracts without code or tests; contracts as JSON |
| `scripts/spec_handoff.py` | generates GitHub issue drafts from accepted specs |
| `.github/workflows/spec-check.yml` | CI: checker on every spec change, models when any exist |
| `CLAUDE.md` | rules for Claude Code; append to your own if you have one |
| `examples/salon/` | worked example with a model; not needed in your repo |

## Steps
1. Copy `specs/`, `.claude/`, `scripts/`, `.github/` and `CLAUDE.md` into the repo root (merge `CLAUDE.md` if one exists).
2. `python scripts/spec_check.py --write-index` should print `0 errors`.
3. Optional: try the example. `python scripts/spec_check.py --root examples/salon/specs`, then `python scripts/spec_model.py fetch-tlc` and `python scripts/spec_model.py --root examples/salon/specs run --all`.
4. In Claude Code: `use spec-clarify: <your rough idea>`, then `spec-write`, optionally `spec-model`.
5. Implementation: Claude Code follows `CLAUDE.md` (contracts, ID mentions in code and tests); check with `python scripts/spec_trace.py coverage --src <dirs> --tests <dirs>`.
6. Review and merge the spec PR (set `status: accepted`), then `use spec-handoff`. It needs `gh` logged in and creates issues only after you confirm.

## Notes
- The CI model job downloads TLC from the official release and checks its SHA-256; it does nothing while `specs/models/` is empty.
- Keep `specs/_work/` out of git (it ships with a `.gitignore`).
