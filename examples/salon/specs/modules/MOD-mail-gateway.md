---
id: MOD-mail-gateway
kind: module
status: draft
version: 1
summary: External email delivery service, as used by this system (fictional vendor)
depends_on: []
supersedes: []
decided_by: []
retired: []
refs: ["https://mail.example.test/api@2026-01-15"]
---
# Mail Gateway

- Kind: external
- Responsibility: delivers email on behalf of the Appointment Service.

## Interface
<!-- External operations state our side of the contract: what we ensure, what we rely on, how it fails. -->
### OP-SendMail
- Sig: `(to, template, params) -> Delivered`
- Pre: the recipient is a deliverable address and the template exists
- Post: a message rendered from the template is queued for the recipient
- Errors: DeliveryFailed: the gateway rejects or cannot queue the message (REQ-010)

## Constraints
- REQ-010 [unwanted] If the Mail Gateway reports DeliveryFailed, then the Appointment Service shall retry the delivery.
