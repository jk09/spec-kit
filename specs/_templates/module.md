---
id: MOD-<slug>
kind: module
status: draft
version: 1
summary: <at most 110 characters: what the module is responsible for>
depends_on: []
supersedes: []
decided_by: []
retired: []
refs: []
---
# <Module term exactly as in the glossary>

- Kind: internal | external
- Responsibility: <one line, glossary terms>

## Interface
<!-- One OP block per operation (glossary operation). Internal modules inherit the contract of the action they implement. -->
### OP-<Operation>
- Sig: `(<args>) -> <Result>`
- Implements: <ACT id>

<!-- External modules (pin the vendor doc in `refs`): state our side of the contract instead of Implements. -->
<!--
### OP-<Operation>
- Sig: `(<args>) -> <Result>`
- Pre: <what we must ensure before calling>
- Post: <what we rely on afterwards>
- Errors: <ErrorName: condition (REQ-nnn)> where the REQ states our reaction
-->

## Constraints
<!-- Optional EARS lines (REQ-nnn) about limits, timeouts, ownership. -->
