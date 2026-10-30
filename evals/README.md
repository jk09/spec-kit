# Skill evals

Cases for the model-driven skills. Run each in a fresh Claude Code session in a copy of the kit, then grade with the commands shown. `tests_kit/test_checker_mutations.py` already covers the checker side without a model.

| # | Skill | Prompt | Pass when |
|---|---|---|---|
| 1 | spec-clarify | `use spec-clarify: customers can reschedule an Appointment` (answer its questions) | `specs/_work/*.brief.md` exists; no `specs/` file other than `_work` changed; every unanswered point is listed as an open question |
| 2 | spec-write | rewrite the brief from case 1 into specs | `python scripts/spec_check.py --strict` prints `0 error(s)`; new specs are `draft`; no `Avoid` synonym used |
| 3 | spec-write | ask it to set `status: accepted` while an `OQ` blocks the spec | it refuses and names the blocking `OQ` |
| 4 | spec-write | change an accepted spec's `Pre` without an ADR | it stops and asks for an ADR before editing |
| 5 | implementation | implement an accepted `ACT` with `CLAUDE.md` loaded | `spec_trace.py coverage --strict` passes for it; `git diff --stat` shows no `specs/` file |
| 6 | implementation | task cites a `draft` spec | it stops and asks instead of coding |
| 7 | spec-handoff | `use spec-handoff` on the salon example | issue drafts cite IDs and copy no requirement text; nothing is created before confirmation |

Record the model, date and result of each run in the PR that changes a skill.
