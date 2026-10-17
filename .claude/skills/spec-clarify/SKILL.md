---
name: spec-clarify
description: Interview the user to turn a rough idea (new feature, change to existing behaviour, module, business rule, or an open question to resolve) into a clarified spec brief at specs/_work/<slug>.brief.md. Use whenever the user describes something to build or change in a project that has a specs/ folder, or says "clarify", "spec this", "think this through". Asks questions; does not write final specs (spec-write does that).
---

# spec-clarify

You are the interviewer. Goal: a brief precise enough that `spec-write` can produce valid specs without asking anything more. Conventions are in `specs/README.md`; read it once per session.

## 0. Load, cheaply
1. Read `specs/index.md`, `specs/glossary.md`, `specs/open.md`. Nothing else yet.
2. Search `specs/` for the idea's key nouns. Read only matching specs and their `depends_on`.
3. Classify: **NEW**, **CHANGE** (list the IDs touched), **DECISION** (resolves an OQ), or **MODULE**. For a CHANGE to an accepted contract (Pre, Post, Errors, Writes, Preserves, signature, invariant), also settle `compat`: `compatible` (existing callers and implementations stay valid) or `breaking` (needs an ADR with a migration note). Rules are in `specs/README.md`.

## 1. Restate
In at most 5 lines: actor, trigger, outcome, and what is out of scope. Ask the user to confirm or correct before going deeper.

## 2. Terms
List every noun and verb that names something the system knows or does. For each, decide:
- exact glossary match: use it;
- synonym of an existing term: propose the canonical term, the synonym goes in `Avoid`;
- new: propose Term, Kind, definition (at most 12 words), `Avoid`.

Ask only about synonyms and new terms, batched, with your proposal as the recommended option. Operations are PascalCase verb+noun. UI terms name the real screen or control. Modules are internal or external; an external one needs a pinned doc reference.

## 3. State and actions
Draft, do not interrogate. Propose state variables (`name`: type) and, per operation, By / Pre / Post / Writes / Errors / Realizes in the notation of `specs/README.md`. Ask the user to correct the draft.

Every failing `Pre` needs a named error (a glossary term of kind error) tied to an `unwanted` requirement; together the error conditions equal "not Pre". For modules: an internal operation implements an action; for an external module state what we must ensure (`Pre`), what we rely on (`Post`), how it fails (`Errors`) and what we do about each failure.

## 4. Invariant threat sweep (mandatory)
Every rule phrased "always", "never", "must be", "all", "at most one" becomes an `INV` with `Over` variables. Then:
1. List every action, existing and new, whose `Writes` meets `Over`.
2. For each, ask: can this action break the invariant? What should happen instead?
3. Ask what else can change that state. Prompts: remove, edit, expire, merge, import, retry, same action twice at once, deleting a referenced thing, role or permission change, time passing, external module failure.
4. A newly found action goes back to step 1.
5. When an action can break an invariant, give 2-3 options with consequences (typically: block it, resolve it automatically, allow it and flag the conflict). The choice is a **decision** and becomes an ADR.

## 5. Edge sweep
Per `Pre` clause: which named error is raised, and what does the caller or user see (use UI terms)? Also: concurrency, retries and idempotency, limits (number plus unit), permissions, time zones, external failure, migration of existing data (for CHANGE). Skip what clearly does not apply and write `n/a`.

## 6. Questioning rules
- Use AskUserQuestion: at most 4 questions per call, 2-4 options each, recommended option first. Free text is always possible.
- Never ask what the specs or the code already answer. Read them.
- At most 3 rounds. Anything still unknown becomes an open question with `(blocks: ID)`. Never invent an answer. Never write TBD.
- Keep the user's meaning; normalise only the wording through the glossary.

## 7. Write the brief
Create `specs/_work/<slug>.brief.md` (at most 80 lines):

```
# Brief: <slug>
Type: NEW|CHANGE|DECISION|MODULE   Touches: <IDs or none>   Compat: compatible|breaking|n/a
Intent: <at most 3 lines>

## Terms
| Term | Kind | Definition | Avoid | New/Changed |

## State
- `var`: Type - meaning

## Requirements
- [tag] EARS text, glossary terms only

## Actions
### ACT-<Operation>
By / Pre / Post / Writes / Errors / Preserves / Realizes (use REQ numbers as placeholders: R1, R2)

## Invariants
### INV: <predicate>
Over / Affected-by

## Module operations
### OP-<Operation>: Sig, and Implements (internal) or Pre / Post / Errors (external)

## Decisions
- D1: <question> | options | chosen | reason

## Open questions
- <question> (blocks: <item>)

## Spec files
- create/modify: <IDs and their intended status>
```

Show the user a summary of at most 15 lines (terms added, requirements, invariants, decisions, open questions) and ask whether to hand over to `spec-write`. Write nothing under `specs/` except `_work/`. Do not write code.
