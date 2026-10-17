---
id: MOD-appointment-service
kind: module
status: accepted
version: 1
summary: Internal owner of Schedule and Appointment state
depends_on: [DOM-schedule, FEAT-appointments]
supersedes: []
decided_by: []
retired: []
refs: []
---
# Appointment Service

- Kind: internal
- Responsibility: sole owner and writer of Schedule and Appointment state.

## Interface
<!-- Internal operations inherit Pre, Post and Errors from the action they implement. -->
### OP-BookAppointment
- Sig: `(customer, stylist, slot) -> Appointment`
- Implements: ACT-BookAppointment

### OP-OpenSlot
- Sig: `(stylist, slot) -> ok`
- Implements: ACT-OpenSlot

### OP-CloseSlot
- Sig: `(stylist, slot) -> ok`
- Implements: ACT-CloseSlot

### OP-CancelAppointment
- Sig: `(appt) -> ok`
- Implements: ACT-CancelAppointment
