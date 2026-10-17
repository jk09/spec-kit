---
name: spec-model
description: Model-check risky invariants with TLA+/TLC. Writes specs/models/MDL-<slug>.md mirroring the state, actions and invariants of the specs, runs it, and turns counterexamples into decisions or open questions. Use when the user asks to verify, model-check or stress-test a rule, after spec-write adds or changes an invariant that several actions can affect, or when spec_check.py reports model-stale.
---

# spec-model

The checker proves the bookkeeping; this skill checks the logic: can any sequence of actions break an invariant? The model mirrors the specs. It never changes behaviour.

## 1. Pick what to model
Model an invariant when at least one holds: two or more actions in its `Affected-by`; several actors or concurrent use; uniqueness, ordering, capacity or money. Skip plain field constraints. If more than 3 candidates, ask the user which.

## 2. Preflight
1. `java -version` works, else tell the user Java is needed.
2. `python scripts/spec_model.py fetch-tlc` if TLC is not found (needs network). If blocked, ask the user to download `tla2tools.jar` and set `TLA2TOOLS_JAR`.
3. Read only the specs being modelled (`depends_on` of the model) and `specs/_templates/model.md`.

## 3. Write `specs/models/MDL-<slug>.md`
Use the template. Mirror the specs exactly; do not repair them here.

| Spec | TLA+ |
|---|---|
| state variable `x`: type | `VARIABLES x`; add to `TypeOK` |
| entity or role set | `CONSTANTS`; the cfg gives it 2-3 model values |
| `ACT-Op` | operator `Op(args) == Pre /\ Post /\ UNCHANGED (vars not in Writes)`, preceded by `\* ACT-Op` |
| map update `f[k -> v]` | `[f EXCEPT ![k] = v]` |
| next-state | `Next` is a disjunction of `\E args \in Sets : Op(args)`, one per action, so traces show action names |
| `INV-nnn` | `INV_nnn == predicate`, preceded by `\* INV-nnn`, and `INVARIANT INV_nnn` in the cfg |

Front matter: `checks` lists exactly the INV IDs in the cfg; `depends_on` lists the spec IDs mirrored; `Scope` states what is abstracted away and the sizes used. No liveness or fairness unless asked.

## 4. Run
```
python scripts/spec_model.py run MDL-<slug> --stamp
```
Exit 0 passes, 1 violation (trace printed), 2 error (syntax, missing INVARIANT, no Java, timeout). `--stamp` records the run and, on success, the spec versions verified.

## 5. Interpret
- **Passes:** report the state count and sizes, and say the result holds for those sizes only. Then do a mutation check: with `extract` to a scratch folder, delete one `Pre` of an action in `Affected-by` and expect a violation. No violation means the invariant or the bounds are too weak; fix the model first.
- **Violated:** restate the trace in glossary terms (who did what, in which order), name the action and invariant, and give 2-3 options (typically block, resolve automatically, allow and flag). That is a decision: hand over to `spec-clarify` (DECISION), which ends in an ADR via `spec-write`. If the user cannot decide now, add `OQ-nnn ... (blocks: INV-nnn)` through `spec-write`. Do not edit spec behaviour yourself.
- **Error:** fix the model. Do not weaken invariants or constants to get a pass.

## 6. After the spec changes
Update the model to mirror it and rerun with `--stamp`. `spec_check.py` warns `model-stale` until the model is verified against the current spec versions.

## 7. Report
At most 8 lines: model ID, invariants checked, sizes, result, trace summary if violated, next step. Models are loaded on demand only; never add them to the default reading order.
