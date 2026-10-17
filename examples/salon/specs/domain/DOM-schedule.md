---
id: DOM-schedule
kind: domain
status: accepted
version: 1
summary: Schedules, Appointments and the rules that tie them together
depends_on: []
supersedes: []
decided_by: [ADR-0001]
retired: []
refs: []
---
# Schedule and Appointment state

## State
- `schedule`: Stylist -> set of Slot - Slots each Stylist offers
- `appointments`: set of Appointment - each has customer, stylist, slot

## Invariants
### INV-001
forall a in appointments: a.slot in schedule[a.stylist]
- Over: schedule, appointments
- Affected-by: ACT-BookAppointment, ACT-CancelAppointment, ACT-CloseSlot, ACT-OpenSlot

### INV-002
forall a, b in appointments: a != b => (a.stylist, a.slot) != (b.stylist, b.slot)
- Over: appointments
- Affected-by: ACT-BookAppointment, ACT-CancelAppointment
