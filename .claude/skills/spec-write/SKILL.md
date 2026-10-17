---
name: spec-write
description: Author or update spec files under specs/ from a clarified brief (specs/_work/*.brief.md) or from a small, unambiguous edit. Allocates IDs, updates the glossary, writes files from specs/_templates, regenerates the index, runs the checker and fixes what it reports. Use after spec-clarify, when asked to "write the specs", accept a spec, or amend an existing spec.
---

# spec-write

Turn decided content into valid spec files. You do not decide behaviour here; unresolved questions go back to `spec-clarify` or into `specs/open.md`.

## 1. Input
- A brief in `specs/_work/`: use it.
- No brief and the change is more than a typo or wording fix: run `spec-clarify` first.

## 2. Preflight
1. Read `specs/README.md` (once per session), `specs/index.md` (its last line gives the next free IDs), `specs/glossary.md`.
2. Read each existing spec you will modify. Nothing else.
3. Check the status of every spec you will modify (see "Changing accepted specs").

## 3. Write, in this order
Glossary, domain, modules, features, decisions, `open.md`. Use `specs/_templates/*`; delete the guidance comments; fill the whole front matter. File name equals `id`, folder follows `kind`.

- Assign real IDs from the index (REQ-nnn, INV-nnn, ADR-nnnn, OQ-nnn); replace the brief's R1, R2 placeholders.
- New specs start as `draft`. Set `accepted` only when the user says so (see below).
- Terse and normative. No rationale (that is the ADR), no history (git), no copied text (reference IDs).
- Only glossary terms, spelled exactly; no `Avoid` synonyms.
- One `shall` per requirement. Numbers carry units. No TBD: use an open question with `(blocks: ID)`.
- For each invariant, `Affected-by` lists every action whose `Writes` meets `Over`, and each of those actions lists the invariant in `Preserves`.
- Every action realizes at least one requirement; `Writes` equals the primed variables in `Post`.
- Every action has `Errors`: each failing `Pre` has a named error (glossary kind error) citing an `unwanted` requirement the action realizes; `none` only when `Pre` is `true`.
- Module specs: one `OP-<Operation>` block per interface operation. Internal: `Sig` and `Implements`, nothing restated. External: `Sig`, `Pre`, `Post`, `Errors`.
- Keep each file under 150 lines; split by feature if larger.

## 4. Changing accepted specs
- Edit in place, bump `version`, add the ADR to `decided_by`. A behaviour change without an ADR is a smell: stop and write the ADR first.
- Deleted items (REQ, INV, ACT, OP) go into `retired`; never reuse their IDs.
- If a contract changes (Pre, Post, Errors, Writes, Preserves, a signature, an invariant, or the pinned `refs` of an external module), set `compat: compatible` or `compat: breaking`. `compatible` means Pre only weaker, Post only stronger, Writes not wider, Preserves not fewer, no new Errors, same signature, nothing removed. Anything else is `breaking` and needs a new ADR in `decided_by` that says how callers migrate.
- Replacing a whole spec: write the new spec with `supersedes: [old-id]` and set the old one to `superseded`.
- Never change `accepted` back to `draft`.

## 5. Accepting
When the user says to accept named specs: set `status: accepted`. Preconditions: their dependencies are accepted and no open question blocks their items. If either fails, report it and do not accept.

## 6. Check
```
python scripts/spec_check.py --write-index
python scripts/spec_check.py --strict --base origin/main
```
(omit `--base` if there is no such ref). Fix every finding and rerun, at most 3 times. If findings remain, report them verbatim; do not weaken the specs to silence the checker.

## 7. Report
At most 10 lines: files created or changed (by ID), new glossary terms, ADRs, open questions, checker result, and one next step (accept, or hand over to implementation by opening issues that cite the REQ and INV IDs). Delete the brief from `specs/_work/` unless the user wants to keep it.
