---
name: dotplot-whats-changed
description: |
  Compare a product's current numbers with the previous Dot Plot report —
  what moved since last time, and whether the change is big enough to mean
  anything.
  Use when the user asks about change over time: "what changed since last time",
  "지난번 대비 어때", "did that fix work", "is retention improving",
  "compare with last week", "did the onboarding change help".
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# What changed since last time

Snapshots are saved locally to `./.dotplot/history.json` every time a report is
made. This reads them.

## 1. Use the same data source and the same value event

A comparison is only meaningful if both sides were measured the same way. Pull
the events the same way as before (same query, same tables), and pass the same
`value_event` — switching from `purchase` to `signup` between runs produces a
dramatic-looking change that means nothing.

Call `history_compare`, or `analyze` (which saves a new snapshot and shows the
comparison card in the report).

## 2. Trust the tool when it says there's nothing to compare

Only snapshots of the **same dataset** are compared — matched by a fingerprint
of the user IDs, not by the file name or the event name. So:

- First run on this product → `note` says there's no history yet. Say that
  plainly. Don't imply nothing changed.
- Analyzed a different product from the same folder → it won't be compared, on
  purpose. Two products both using the event name `purchase` are not the same
  product.

## 3. Read the size of the move, not just the direction

Every rate in the comparison has a denominator. With 30 users, one person
changes churn by 3 points — a "5 point improvement" is two people changing their
minds. State the user counts alongside the percentages.

A move is worth acting on when it's larger than a few users' worth of noise, and
when you can point at something that changed in the product to explain it.

## 4. Connect it to what they did

The useful version of this answer is not "regular_rate went from 8% to 14%". It
is "the onboarding change you shipped on the 5th is followed by more users
reaching a second week — worth continuing, though it's 25 users so far."

If they shipped nothing in between, say that too. Metrics drift on their own,
and reading meaning into that drift is how teams end up chasing noise.
