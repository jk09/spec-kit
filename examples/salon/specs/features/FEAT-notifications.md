---
id: FEAT-notifications
kind: feature
status: draft
version: 1
summary: Email the Customer when an Appointment is cancelled
depends_on: [FEAT-appointments, MOD-mail-gateway]
supersedes: []
decided_by: []
retired: []
refs: []
---
# Notifications

## Requirements
- REQ-008 [event] When an Appointment is cancelled, the Appointment Service shall send a cancellation notice to the Customer through the Mail Gateway.
