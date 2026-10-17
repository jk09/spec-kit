# Salon example

The booking scenario from the FizzBee article, written in this kit's format. Run from the kit root:

```
python scripts/spec_check.py --root examples/salon/specs
```

Try breaking it:
- In `DOM-schedule.md`, delete `ACT-CloseSlot` from INV-001's `Affected-by`: the checker names the missing action. This is the "stylist removes availability" gap, surfaced by bookkeeping alone.
- In `FEAT-appointments.md`, delete `INV-001` from ACT-CloseSlot's `Preserves`: error.
- In `open.md`, change `(blocks: REQ-010)` to `(blocks: REQ-007)`: an open question now blocks an accepted spec.

- In `FEAT-appointments.md`, delete the `SlotTaken` entry from ACT-BookAppointment's `Errors`: warnings that REQ-003 is cited by no error and the glossary term is unused (delete all `Errors` entries to get the hard error).
- In `MOD-appointment-service.md`, delete an `Implements` line: the operation has no contract.
- Bump nothing but change an accepted `Post`, then run with `--base`: version and `compat` rules fire.

`FEAT-notifications` stays `draft` while OQ-001 is open (it blocks REQ-010, the retry rule for `MOD-mail-gateway`, an external module with its own `Pre`, `Post` and `Errors`). `ADR-0001` records the choice made for closing a booked Slot (reject it).

What the checker cannot tell you is whether `Pre` of CloseSlot really keeps INV-001 true. That needs a model (`models/`, FizzBee or TLA+).

## The model
`models/MDL-appointments.md` mirrors the actions in TLA+. With Java installed:

```
python scripts/spec_model.py fetch-tlc
python scripts/spec_model.py --root examples/salon/specs run MDL-appointments
```

It passes (256 distinct states). Now delete the `/\ \A a \in appointments : ...` line from `CloseSlot` in the model, which is the article's bug, and rerun: TLC returns a trace of three actions (OpenSlot, BookAppointment, CloseSlot) that breaks INV-001. That is how a missing `Pre` shows up, and the fix is the decision recorded in ADR-0001.
