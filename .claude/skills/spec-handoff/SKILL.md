---
name: spec-handoff
description: Turn accepted specs into GitHub issues that Claude Code (or a developer) can implement, citing REQ/INV/ACT IDs instead of copying text. Use when the user says "hand off", "create issues from the specs", "ready to implement", or after specs have been accepted and merged. Creates issues only after the user confirms the list.
---

# spec-handoff

Issues are thin pointers into `specs/`. The spec stays the single source of truth.

## 1. Preconditions
1. `python scripts/spec_check.py --strict` passes.
2. The specs to hand off have `status: accepted` and are on the default branch (issues cite file paths, and implementers read them from there). If they are only on a feature branch, say so and ask whether to continue.
3. `gh auth status` works. If not, stop and tell the user.

## 2. Generate drafts
```
python scripts/spec_handoff.py                  # all accepted feature specs
python scripts/spec_handoff.py --spec FEAT-x    # named accepted specs (any kind)
```
It writes `specs/_work/issues/<ID>.v<N>.md` and prints `ID<TAB>title<TAB>file<TAB>labels` in dependency order. It skips draft specs and specs blocked by open questions, and reports why. If git history holds an earlier version of a spec, the issue is "Update ... to vN" with a delta of added, changed and retired items; use `--full` only if the user wants the whole spec re-implemented.

## 3. Skip what already exists
For each line, search by title (titles are deterministic):
```
gh issue list --state all --search 'in:title "<title up to the colon>"' --json number,title,state
```
If an issue for that ID and version exists, skip it and note its number.

## 4. Confirm
Show the user a table: ID, title, number of REQ and INV items, existing issue if any. Ask once whether to create the missing ones. Do not create anything before the answer.

## 5. Create, in the printed order
1. Ensure the label: `gh label create spec --color 5319e7 --force`.
2. For each draft, replace the `<!-- blocked-by -->` line with `Blocked by: #n, #m` listing the issues (new or existing) of the specs it `depends_on`, or delete the line if none.
3. `gh issue create --title "<title>" --body-file <file> --label spec --label <kind>`.
4. Record the issue number for later drafts.

Add a comment such as `@claude implement this per CLAUDE.md` only if the user asks for it and the repository has the Claude Code GitHub Action set up. Never assign people or set milestones on your own.

## 6. Report
At most 8 lines: a table of issue numbers and titles, anything skipped and why, and the next step (review the PRs; each must cite the IDs it implements). Delete `specs/_work/issues/` afterwards (it is git-ignored scratch).
