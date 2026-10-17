## Specifications

Behaviour is defined by `specs/` (conventions: `specs/README.md`). Specs are the source of truth; code follows them.

### Reading order (keep context small)
1. `specs/index.md`, then `specs/glossary.md`. Always.
2. Only the specs the task cites by ID, plus their `depends_on`. Nothing else.
3. `specs/decisions/*` only when a REQ or INV you implement cites an ADR, or you are changing behaviour.

### Implementing
- Implement only `status: accepted` specs. If the task touches a `draft` spec, stop and ask.
- Use glossary terms verbatim for types, functions, UI labels, modules, errors (`ACT-BookAppointment` becomes `BookAppointment`, in your language's casing). Never use an `Avoid` synonym.
- Contracts: `Pre` becomes a guard that fails with the named error from `Errors`, observable by callers. `Post` is verified by a test or a runtime check. Each `INV` gets an invariant or property test, or a runtime check at state boundaries. `Writes` is a limit: change no other state. An internal `OP` has the contract of the action it `Implements`; wrap an external `OP` so its `Pre` is ensured and each `Errors` entry is handled as the cited requirement says.
- Traceability: every code file that enforces a contract and every test that covers one mentions its IDs (name, annotation or comment; any form containing the ID). Every REQ and INV needs a test; every ACT needs code and a test.
- Commits and PRs say what they implement: `Implements REQ-001, REQ-002`.

### When the specs are wrong or silent
- Do not guess. If a spec is ambiguous, contradictory, or the code needs behaviour no spec states, stop that part, say so, and propose a spec change with the `spec-write` skill (rough idea: `spec-clarify` first).
- Never edit an accepted spec in a feature PR. Spec changes go in their own PR (version bump, ADR in `decided_by`) and merge first.

### Spec skills
- `spec-clarify`: interviews the user about a rough idea and produces a brief in `specs/_work/`.
- `spec-write`: turns a brief into valid spec files, updates glossary and index, runs the checker.
- `spec-model`: model-checks risky invariants with TLA+/TLC (`specs/models/`, loaded on demand only).
- `spec-handoff`: turns accepted specs into GitHub issues that cite IDs.

### Before every commit
`python scripts/spec_check.py --strict --base origin/main` must pass. In implementation PRs, also `python scripts/spec_trace.py coverage --src <source dirs> --tests <test dirs> --spec <IDs of the issue>`. If you changed behaviour that a model covers, `python scripts/spec_model.py run --all` must pass too. Never edit `specs/` in a feature PR.
