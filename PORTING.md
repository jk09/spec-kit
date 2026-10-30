# Using the kit with other coding agents

The specs, scripts and CI are agent-neutral. Only two things are Claude Code specific.

| Claude Code | Other agents |
|---|---|
| `CLAUDE.md` | Copy its content to the agent's instruction file (`AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, ...). Keep the section headings. |
| `.claude/skills/*/SKILL.md` | Each file is plain Markdown instructions. Paste one into the agent's prompt, rules or custom-command feature when its stage is needed (`spec-clarify`, then `spec-write`, `spec-model`, `spec-handoff`). |

Enforcement does not depend on the agent:
- `spec_check.py --strict --base origin/main` (workflow `spec-check`)
- `spec_trace.py coverage --strict` and `spec_guard.py` (workflow `spec-enforce`)
- `CODEOWNERS` with branch protection "Require review from Code Owners" keeps spec changes with their owners.

Whichever agent you use, require the same sequence: read `specs/index.md` and `specs/glossary.md`, then only the cited specs; implement only `accepted` specs; mention IDs in code and tests; run the checks before pushing.
