---
id: MDL-<slug>
kind: model
status: draft
version: 1
summary: <at most 110 characters: what is modelled>
depends_on: [<DOM and FEAT ids mirrored>]
supersedes: []
decided_by: []
retired: []
refs: []
checks: [INV-000]
verified_against: []
---
# <Model title>

- Tool: TLA+
- Scope: <actions and state included, set sizes used, what is abstracted away>
- Last run: never

```tla
---- MODULE <Name> ----
\* Mirrors <spec ids>. INV-000 is INV_000 here.
EXTENDS Naturals
CONSTANTS <Sets>

VARIABLES <state variables, same names as the spec>
vars == <<<state variables>>>

TypeOK == <types of all variables>

Init == <initial values>

\* ACT-<Operation>
<Operation>(<args>) ==
    /\ <Pre>
    /\ <Post, primed variables>
    /\ UNCHANGED <variables not in Writes>

Next == \/ \E <args> \in <Sets> : <Operation>(<args>)

Spec == Init /\ [][Next]_vars

\* INV-000
INV_000 == <predicate>
====
```

```cfg
SPECIFICATION Spec
CONSTANTS
    <Sets> = {m1, m2}
INVARIANT TypeOK
INVARIANT INV_000
```
