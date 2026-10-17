---
id: FEAT-appointments
kind: feature
status: accepted
version: 1
summary: Booking, cancelling, opening and closing Slots
depends_on: [DOM-schedule]
supersedes: []
decided_by: [ADR-0001]
retired: []
refs: []
---
# Appointments

## Requirements
- REQ-001 [event] When a Customer submits the Booking Form, the Appointment Service shall run ACT-BookAppointment.
- REQ-002 [unwanted] If the requested Slot is not in the Stylist's Schedule, then the Appointment Service shall reject the request.
- REQ-003 [unwanted] If the requested Slot already holds an Appointment, then the Appointment Service shall reject the request.
- REQ-004 [event] When a Stylist submits the Schedule Editor with a Slot to open, the Appointment Service shall run ACT-OpenSlot.
- REQ-005 [event] When a Stylist submits the Schedule Editor with a Slot to close, the Appointment Service shall run ACT-CloseSlot.
- REQ-006 [unwanted] If the Slot to close holds an Appointment, then the Appointment Service shall reject the request.
- REQ-007 [event] When a Customer or a Stylist cancels an Appointment, the Appointment Service shall run ACT-CancelAppointment.
- REQ-009 [unwanted] If the Appointment to cancel does not exist, then the Appointment Service shall reject the request.

## Actions
### ACT-BookAppointment
- By: Customer
- Pre: slot in schedule[stylist] and no a in appointments with a.stylist = stylist and a.slot = slot
- Post: appointments' = appointments + {Appointment(customer, stylist, slot)}
- Writes: appointments
- Preserves: INV-001, INV-002
- Realizes: REQ-001, REQ-002, REQ-003
- Errors: OutsideSchedule: the Slot is not in the Stylist's Schedule (REQ-002); SlotTaken: an Appointment already holds the Slot (REQ-003)

### ACT-OpenSlot
- By: Stylist
- Pre: true
- Post: schedule' = schedule[stylist -> schedule[stylist] + {slot}]
- Writes: schedule
- Preserves: INV-001
- Realizes: REQ-004
- Errors: none

### ACT-CloseSlot
- By: Stylist
- Pre: no a in appointments with a.stylist = stylist and a.slot = slot
- Post: schedule' = schedule[stylist -> schedule[stylist] - {slot}]
- Writes: schedule
- Preserves: INV-001
- Realizes: REQ-005, REQ-006
- Errors: SlotBooked: an Appointment holds the Slot (REQ-006)

### ACT-CancelAppointment
- By: Customer, Stylist
- Pre: appt in appointments
- Post: appointments' = appointments - {appt}
- Writes: appointments
- Preserves: INV-001, INV-002
- Realizes: REQ-007, REQ-009
- Errors: AppointmentNotFound: the Appointment does not exist (REQ-009)
