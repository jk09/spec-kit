---
id: FEAT-<slug>
kind: feature
status: draft
version: 1
summary: <at most 110 characters: behaviour covered>
depends_on: []
supersedes: []
decided_by: []
retired: []
refs: []
---
# <Feature title>

## Requirements
<!-- EARS, one `shall` per line. Tags: ubiq event state unwanted option complex. Glossary terms only. Every failing Pre needs an `unwanted` requirement. -->
- REQ-000 [event] When <trigger>, the <Module> shall <response>.

## Actions
<!-- One block per operation. Heading ACT-<Operation> (glossary operation, PascalCase). -->
### ACT-<Operation>
- By: <Role>
- Pre: <predicate; `true` if none>
- Post: <v' = ... for every variable in Writes>
- Writes: <state variables>
- Preserves: <INV ids this action must keep true>
- Realizes: <REQ ids, including the unwanted ones cited in Errors>
- Errors: <ErrorName: condition (REQ-nnn); ...> or `none` only when Pre is `true`
