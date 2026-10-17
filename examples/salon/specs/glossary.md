# Glossary

<!-- Canonical vocabulary. Spec text uses these spellings exactly. Avoid = banned synonyms (checked). Kinds: entity role operation error ui module external enum event. Operations are PascalCase (ACT-<Operation>). -->

| Term | Kind | Definition | Avoid |
|---|---|---|---|
| Customer | role | Person who books Appointments | client, user, patron |
| Stylist | role | Staff member who serves Appointments | hairdresser, employee, staff |
| Appointment | entity | A Customer's reservation of one Slot with one Stylist | reservation, session |
| Slot | entity | Thirty-minute interval on the half hour that a Stylist can work | timeslot, time slot, window |
| Schedule | entity | The set of Slots a Stylist offers | availability, calendar, roster |
| BookAppointment | operation | Customer reserves a Slot with a Stylist | reserve |
| CancelAppointment | operation | Customer or Stylist removes an Appointment | |
| OpenSlot | operation | Stylist adds a Slot to own Schedule | add availability |
| CloseSlot | operation | Stylist removes a Slot from own Schedule | block slot |
| SendMail | operation | Ask the Mail Gateway to deliver one email | |
| OutsideSchedule | error | Requested Slot is not in the Stylist's Schedule | |
| SlotTaken | error | Requested Slot already holds an Appointment | |
| SlotBooked | error | Slot to close holds an Appointment | |
| AppointmentNotFound | error | Appointment to cancel does not exist | |
| DeliveryFailed | error | Mail Gateway could not deliver the email | |
| Booking Form | ui | Screen where a Customer picks a Slot and confirms | booking page, booking screen |
| Schedule Editor | ui | Screen where a Stylist opens and closes Slots | availability page, calendar editor |
| Appointment Service | module | Internal module that owns Schedules and Appointments | booking service, scheduler |
| Mail Gateway | external | Third-party service that delivers email | smtp relay, email provider |

## Ignore

<!-- Capitalised words that are not domain terms (proper nouns, product names), comma-separated. -->
