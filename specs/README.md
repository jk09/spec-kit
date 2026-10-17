# Specs: conventions

Normative, formal, checkable, platform-neutral. Rationale lives in `decisions/`, history lives in git.
Check everything with `python scripts/spec_check.py` (see "Tooling" at the end).

## Layout

```
specs/
  index.md       generated table of all specs; load first
  glossary.md    canonical terms; single source of truth
  open.md        open questions (OQ-nnn)
  domain/     DOM-<slug>.md    state + invariants
  features/   FEAT-<slug>.md   EARS requirements + actions
  modules/    MOD-<slug>.md    internal and external module interfaces
  decisions/  ADR-nnnn.md      options, decision, consequences
  models/     MDL-<slug>.md    optional TLA+ for risky invariants
  _templates/ skeletons        _work/ scratch briefs (git-ignored)
```

## Front matter (every spec)

| Field | Rule |
|---|---|
| `id` | `DOM-x`, `FEAT-x`, `MOD-x`, `MDL-x` (lowercase slug) or `ADR-0001`; equals the file name |
| `kind` | domain, feature, module, decision, model (decides the folder) |
| `status` | draft, accepted, superseded, deprecated |
| `version` | integer, starts at 1; bump on every change to an accepted spec |
| `summary` | at most 110 characters; shown in the index |
| `depends_on` | spec IDs that must be read with this one (no cycles) |
| `supersedes` | spec IDs this one replaces; those become `superseded` |
| `decided_by` | ADR IDs behind this version's content |
| `retired` | item IDs (REQ, INV, ACT, OP) deleted from this spec; reserved forever |
| `refs` | outside material, pinned: `"<url or repo path>@<revision>"` |
| `compat` | `compatible` or `breaking`; required when an accepted contract changes (see Contracts) |
| `checks` | (model only) INV IDs the model verifies |
| `verified_against` | (model only) `"<spec id>@<version>"` list, written by `spec_model.py --stamp` |

## Identifiers

- Items: `REQ-nnn`, `INV-nnn`, `OQ-nnn` (global, 3 digits), `ADR-nnnn`.
- Actions `ACT-<Operation>` (business operations) and module operations `OP-<Operation>`; `<Operation>` is a glossary term of kind operation.
- Never renumber or reuse an ID. Next free numbers are printed at the bottom of `index.md`.
- Reference by ID. Never copy text from another spec.

## Glossary

One table row per term: `Term | Kind | Definition | Avoid`.
Kinds: entity, role, operation, error, ui, module, external, enum, event.

- Terms are Capitalised (operations and errors PascalCase) and used exactly so in specs, including plurals.
- `Avoid` lists banned synonyms; the checker rejects them.
- UI terms name the real screen or control. Module terms name internal or external modules. Error terms name outcomes callers can tell apart.
- Add a term before using it. Delete terms nothing uses.

## Notation

EARS requirements, one per line: `- REQ-nnn [tag] <text>` with exactly one `shall`.

| Tag | Template |
|---|---|
| ubiq | The Module shall response. |
| event | When trigger, the Module shall response. |
| state | While state, the Module shall response. |
| unwanted | If condition, then the Module shall response. |
| option | Where feature, the Module shall response. |
| complex | Two or more of When/While/Where/If, comma-separated, one `shall`. |

Formal fragments (TLA+-flavoured, ASCII):

- State: `` - `var`: Type - meaning ``. Types: `set of T`, `T -> U` (map), `T x U` (pair).
- Predicates: `forall x in S: P`, `exists x in S: P`, `no x in S with P`, `and`, `or`, `not`, `=>`, `=`, `!=`, `in`, `+` (union), `-` (difference), `{a, b}`.
- `v'` is `v` after the action. `f[k -> x]` is map `f` with `k` set to `x`. Variables not in `Writes` are unchanged.
- Action `ACT-<Operation>`: `By`, `Pre`, `Post` (`v' = ...` for every variable in `Writes`), `Writes`, `Preserves`, `Realizes`, `Errors`.
- `Errors`: `Name: condition (REQ-nnn); Name: condition (REQ-nnn)`, or `none` only when `Pre` is `true`. Each name is a glossary error; each REQ is an `unwanted` requirement the action realizes. The conditions together equal "not `Pre`".
- Invariant `INV-nnn`: a predicate true in every reachable state, plus `Over` (state variables it mentions) and `Affected-by` (every action whose `Writes` meets `Over`).
- Module operation `### OP-<Operation>` in a module spec. Internal module: `Sig` and `Implements: ACT-...`; the contract is inherited, nothing is restated. External module: `Sig`, `Pre` (what we must ensure), `Post` (what we rely on), `Errors` (how it fails; each cites an `unwanted` requirement stating our reaction).

## Contracts (Design by Contract)

| Concept | Where |
|---|---|
| Precondition | `Pre` of an action or external operation |
| Postcondition | `Post` |
| Failure behaviour | `Errors` and the `unwanted` requirements they cite |
| System invariant | `INV` with `Over`, `Affected-by`; actions list it in `Preserves` |
| Frame condition (what may change) | `Writes`, equal to the primed variables of `Post` |
| Interface contract | `OP` blocks in module specs |
| Substitutability | `compat` |

Obligations on any implementation, in any language:
- `Pre` becomes a guard that fails with the named error outcome, observable by callers.
- `Post` is verified by a test, or by a runtime check where the platform offers one.
- `INV` gets an invariant or property test, or a runtime check at state boundaries.
- `Writes` is a limit: the action changes no other state.
- An internal `OP` has exactly the contract of the action it implements. An external `OP` is wrapped so its `Pre` is ensured and each of its `Errors` is handled as the cited requirement says.

Compatibility. When an accepted contract changes (`Pre`, `Post`, `Errors`, `Writes`, `Preserves`, a signature, an invariant, a removed operation, or the pinned `refs` of an external module), declare `compat`:
- `compatible`: existing callers and implementations stay valid. `Pre` only weaker, `Post` only stronger, `Writes` not wider, `Preserves` not fewer, no new `Errors`, same `Sig`, nothing removed. The checker verifies the mechanical parts; weaker/stronger is the author's attestation (a model can back it).
- `breaking`: anything else. Needs a new ADR in `decided_by` that says how callers migrate.

## Traceability

Code that enforces a contract mentions its ID anywhere in the file (comment, name, annotation); a test that covers it does the same. `python scripts/spec_trace.py coverage --src <dirs> --tests <dirs>` reports accepted contracts with no evidence: every REQ and INV needs a test, every ACT and external OP needs source and a test. `spec_trace.py export` writes all accepted contracts as JSON for generators or reviewers. This proves traceability, not correctness.

## Models

Optional, for invariants several actions can break. A model is one file in `models/` with a `- Tool: TLA+` line, a ```tla block and a ```cfg block. It mirrors the specs and never changes behaviour.

- Variables keep their spec names; actions are operators named like the glossary operation; `INV-001` is `INV_001` in TLA+.
- Keep sets small (2-3 model values) and say so in `Scope`.
- `python scripts/spec_model.py run MDL-x --stamp` runs TLC (needs Java; `fetch-tlc` downloads it). A violation prints the trace; it becomes a decision (ADR) or an open question.
- `spec_check.py` warns `model-stale` when a spec the model depends on has a newer version than the one verified.
- Models are not versioned like specs and are loaded on demand only. FizzBee models (`- Tool: FizzBee`, ```fizzbee block) pass the checker but are not run by `spec_model.py`.

## Writing rules

1. One normative statement per line. No rationale, history, or examples in specs; use an ADR.
2. Only `shall`. Never should, may, normally, usually, appropriate, fast, easy, and/or, etc.
3. Numbers carry units. No TBD or TODO: write an `OQ-nnn` with `(blocks: ID, ID)` in `open.md`.
4. Every invariant names every action that can affect it; every such action preserves it. Ask "what else can change this state?" until nothing new appears.
5. Every action realizes at least one requirement and has `Errors`; every failing `Pre` has a named error and an `unwanted` requirement.
6. Budget: a spec stays under 150 lines or 2500 tokens; split by feature otherwise.
7. Outside material is pinned to a revision in `refs`.

## Lifecycle

- `draft`: may change freely. Implementation must not start.
- `accepted`: implementable. Requires no open question blocking its items and accepted dependencies.
- Changing an accepted spec: bump `version`, add the ADR to `decided_by`, put deleted items in `retired`, set `compat` if a contract changed.
- Replacing a whole spec: new spec with `supersedes`; the old one becomes `superseded`.
- `deprecated`: still true of the code, scheduled for removal.

## Tooling

```
python scripts/spec_check.py [--write-index] [--strict] [--base origin/main]   consistency
python scripts/spec_model.py run MDL-x|--all [--stamp]                         model checking
python scripts/spec_trace.py coverage | export                                 traceability, contracts as JSON
python scripts/spec_handoff.py [--spec ID]                                     GitHub issue drafts
```

`spec_check.py` verifies: model files and staleness, front matter, IDs and references, glossary terms and banned synonyms, EARS shape, state/action/invariant bookkeeping (`Writes` vs `Post`, `Over` vs `Affected-by` vs `Preserves`), `Errors` against `Pre` and `unwanted` requirements, module operations, status rules, pinned refs, size budgets, index freshness. With `--base`: accepted specs changed without a version bump, deleted accepted specs, IDs removed without `retired`, contract changes without `compat`, widened or breaking changes declared compatible.
It does not prove that an action really preserves an invariant; that is what `models/` is for.

Skills in `.claude/skills/`: `spec-clarify`, `spec-write`, `spec-model`, `spec-handoff`. `.github/workflows/spec-check.yml` runs the checker (with `--base` on pull requests) and the models.
