---
name: dotplot-add-tracking
description: |
  Find the product actions that aren't being logged and write the logging for
  them, then say how long to wait before the data can be analyzed.
  Use when the user has nothing to analyze yet, or when Dot Plot reports that no
  event in the data can serve as a value event: "add the tracking I'm missing",
  "추적 안 되는 거 심어줘", "we don't track anything", "set up analytics",
  "what should I be logging", "why is there no data".
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Edit
  - Write
---

# Add the tracking that's missing

A product that records nothing can't be analyzed — but it can be read. That is
what this does: find the holes in the code, fill them, and set a date to come
back.

## 1. Read what the code already logs

Search for existing logging calls before assuming there are none:

```
logEvent(   track(   analytics.capture(   posthog.capture(
gtag('event'   mixpanel.track(   amplitude.logEvent(   segment.track(
```

Also check for a database write that serves the same purpose — an `events`,
`activity`, or `audit_log` table being inserted into.

## 2. Ask the code what's missing

Pass what you found to `audit_tracking`. **It does not need a CSV** — call it
with `code_events` alone when there's no data yet.

It answers the question that matters at this stage: whether anything being
logged could ever show that a user got value. A product logging only `open_app`
and `page_view` has tracking and still can't answer anything —
`can_measure_value: false` is the finding, not an error.

With data, it also splits into what fires, what never fires (broken logging, or
a feature nobody uses), and what's in the data but not the code.

## 3. Find what has no logging at all

This is the part the tool can't do and the part that matters most. Read the code
for the product's **core actions** — the handlers behind the buttons that are
the reason the product exists — and check which have no logging near them.

A missing log line appears in neither list. It only shows up if you look.

## 4. Prescribe, don't report

For each hole, write the one line that belongs in that file, in that function,
matching the surrounding style. Follow the project's existing naming — 
`follow_artist` if the codebase is snake_case, `followArtist` if camelCase.

Show it, ask, and apply it if they agree. Don't bulk-edit files without asking.

Choose event names for what they mean, not what's easy: `purchase` not
`button_click`, `send_message` not `submit`. A vanity name can't be undone
later without rewriting history.

## 5. Set the return date

`audit_tracking` returns `come_back_in_days`. Those aren't round numbers picked
for feel — they're how long a user must be observed before the code will judge
them:

- **7 days** — enough to call someone churned
- **14 days** — enough to call someone a regular, and for week-1 retention

Tell them which. Running the analysis tomorrow produces a report with nothing in
it, which reads like the product is failing when it just means the data is young.

Then: `/dotplot-analyze-product` in a week, and `/dotplot-whats-changed` the
week after that.
