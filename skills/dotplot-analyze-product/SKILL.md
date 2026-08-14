---
name: dotplot-analyze-product
description: |
  Analyze a product's real users with Dot Plot: find the event data, pick the
  action that means "this user got value", and produce the dot plot report —
  aha moment, onboarding funnel, weekly retention, and what to do next.
  Use when the user asks anything general about how their users are doing:
  "analyze my product", "우리 서비스 분석해줘", "find my aha moment",
  "are people actually using this", "why are users churning",
  "show me retention", "who are my power users".
  Works without an events table — ordinary tables (orders, sessions, posts)
  become the event log.
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Analyze this product

The statistics come from the `dotplot` MCP server, never from you. Your job is
finding the data, choosing well, and explaining what it means.

## 1. Find the event data

Call `analyze` with no arguments first if you don't already know where the data
is — it returns the procedure. In short:

- Is `DOTPLOT_DB_URL` set? Is there a connection string in `.env`? Is a
  Postgres/Supabase MCP already connected?
- Read the schema. You're looking for tables recording **things users did** —
  `orders`, `sessions`, `posts`, `messages`, `subscriptions`. An `events` table
  is nice but most early products don't have one, and that is fine.
- Turn those tables into events with `load_from_db`, one SELECT per action
  joined by `UNION ALL`:

```sql
SELECT user_id, created_at::date AS date, 'purchase' AS event FROM orders
UNION ALL
SELECT user_id, added_at::date, 'add_to_wishlist' FROM wishlist_items
```

If there's no database and nothing is tracked, say so plainly and switch to
`/dotplot-add-tracking`. Don't invent a report.

## 2. Choose the value event yourself when you can

`analyze` picks the most-repeated non-vanity action, and says why. But you have
read the codebase, so you know things the code cannot: that `purchase` is value
and `view_item` is browsing, even though they look identical in the numbers.
When you know better, pass `value_event` explicitly.

Check the result's `value_event.why` and `others_available`. If the choice looks
wrong, call again — it's cheap.

## 3. Report it like a person

Open the report, then say the headline out loud. Lead with what to do, not with
the numbers.

Three things to get right:

- **The aha moment is a correlation.** Say so. "Users who did X became regulars"
  can mean X causes retention, or that engaged users do everything. The honest
  recommendation is to put it in onboarding and A/B test it — not to declare it.
- **Small numbers deserve hedging.** The report drops weeks with under five
  users, but a rate over 8 users is still thin. Mention the denominator when
  it's small.
- **Match their language.** Pass `lang="ko"`/`"ja"`/`"en"`; for anything else,
  translate `get_report_strings` and use `generate_report` with `lang="custom"`.

Offer `publish_report` only if they want a shareable link — it puts their
numbers on the public web, so ask first.

## When they want one number

They asked for retention, not an analysis — use `retention_curve`,
`onboarding_funnel`, `classify_users`, or `find_aha_moments` directly instead of
generating a whole report.
