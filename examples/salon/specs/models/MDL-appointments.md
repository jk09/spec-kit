---
id: MDL-appointments
kind: model
status: accepted
version: 1
summary: TLA+ model of Slot and Appointment state; checks INV-001 and INV-002
depends_on: [DOM-schedule, FEAT-appointments]
supersedes: []
decided_by: []
retired: []
refs: []
checks: [INV-001, INV-002]
verified_against: ["DOM-schedule@1", "FEAT-appointments@1"]
---
# Appointments model

- Tool: TLA+
- Scope: schedule, appointments; ACT-BookAppointment, ACT-OpenSlot, ACT-CloseSlot, ACT-CancelAppointment; two Stylists, two Customers, two Slots. Notifications abstracted away.
- Last run: 2026-10-17 TLC ok: 256 distinct states, invariants hold: INV-001, INV-002

```tla
---- MODULE Appointments ----
\* Mirrors DOM-schedule and FEAT-appointments. Invariant INV-001 is INV_001 here, and so on.
EXTENDS Naturals
CONSTANTS Stylists, Customers, Slots

VARIABLES schedule, appointments
vars == <<schedule, appointments>>

Appts == [customer: Customers, stylist: Stylists, slot: Slots]

TypeOK == /\ schedule \in [Stylists -> SUBSET Slots]
          /\ appointments \subseteq Appts

Init == /\ schedule = [s \in Stylists |-> {}]
        /\ appointments = {}

\* ACT-BookAppointment
BookAppointment(c, s, t) ==
    /\ t \in schedule[s]
    /\ \A a \in appointments : ~(a.stylist = s /\ a.slot = t)
    /\ appointments' = appointments \cup {[customer |-> c, stylist |-> s, slot |-> t]}
    /\ UNCHANGED schedule

\* ACT-OpenSlot
OpenSlot(s, t) ==
    /\ schedule' = [schedule EXCEPT ![s] = @ \cup {t}]
    /\ UNCHANGED appointments

\* ACT-CloseSlot
CloseSlot(s, t) ==
    /\ \A a \in appointments : ~(a.stylist = s /\ a.slot = t)
    /\ schedule' = [schedule EXCEPT ![s] = @ \ {t}]
    /\ UNCHANGED appointments

\* ACT-CancelAppointment
CancelAppointment(a) ==
    /\ a \in appointments
    /\ appointments' = appointments \ {a}
    /\ UNCHANGED schedule

Next == \/ \E c \in Customers, s \in Stylists, t \in Slots : BookAppointment(c, s, t)
        \/ \E s \in Stylists, t \in Slots : OpenSlot(s, t)
        \/ \E s \in Stylists, t \in Slots : CloseSlot(s, t)
        \/ \E a \in appointments : CancelAppointment(a)

Spec == Init /\ [][Next]_vars

\* INV-001
INV_001 == \A a \in appointments : a.slot \in schedule[a.stylist]
\* INV-002
INV_002 == \A a, b \in appointments : a # b => <<a.stylist, a.slot>> # <<b.stylist, b.slot>>
====
```

```cfg
SPECIFICATION Spec
CONSTANTS
    Stylists = {s1, s2}
    Customers = {c1, c2}
    Slots = {t1, t2}
INVARIANT TypeOK
INVARIANT INV_001
INVARIANT INV_002
```
