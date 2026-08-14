# Tools

`analyze` is the whole product. Everything else is a part it already uses —
reach for one only when you want a single number on its own ("just show me
retention").

| Tool | What it does |
|---|---|
| **`analyze`** | **Data in, finished report out. Start here.** |
| `describe_events` | Shape of the data: date range, users, events by type |
| `dot_plot` | Text dot plot (◎ first day, ● value event, custom marks) |
| `classify_users` | churned / weekend-only / regular / casual, automatically |
| `find_aha_moments` | Scans every action for the one that turns users into regulars |
| `onboarding_funnel` | Signup → first value → returned → still active: where users leak |
| `retention_curve` | Weekly retention — the number investors always ask |
| `load_from_db` | Pull events straight out of Postgres/SQLite into a file |
| `history_compare` | "Since last time" deltas, from snapshots saved on every report |
| `find_similar_cases` | Match your diagnosis to documented cases (Facebook's 7 friends, Slack's 2k messages…) |
| `audit_tracking` | What your code logs vs what arrives — works with no data at all |
| `generate_report` | The HTML report, when you need to control marks or language |
| `publish_report` | Host the report at a random URL and get a share link (Vercel) |
| `submit_benchmark` | Send five aggregates to the anonymous benchmark (consent required) |
| `compare_benchmark` | Compare yourself against similar teams' percentiles |

## Slash commands

Type `/` in Claude Code:

| | |
|---|---|
| `/mcp__dotplot__analyze_product` | Full analysis and report |
| `/mcp__dotplot__add_tracking` | Find and write the logging you're missing |
| `/mcp__dotplot__whats_changed` | Compare with the previous report |

## Input

Three columns — who, when, what: `user_id, date, event`. A `platform` column is
optional and shows up as a label.

CSV, TSV, JSON, and JSONL are all read directly, columns are matched by name
(`uid`, `customer_id`, `created_at`, `event_name`, … all work), and timestamps
are reduced to days. So whatever your database tool already exports is fine:

```bash
psql -c "..." --csv > events.csv           # Postgres
mysql --json -e "..." > events.json        # MySQL
mongoexport --collection=orders ...        # MongoDB
bq query --format=json "..." > events.json # BigQuery
```

That is the whole "which databases are supported" answer: the ones you can
already query. The data goes from your database to a file to the report — it
never passes through the model.

Ambiguous dates are refused rather than guessed. `07/01/2026` is either July 1st
or January 7th, and picking one silently would produce a wrong report.

## Languages

Reports work in any language. English, 한국어, and 日本語 are built in; for
anything else the agent translates the report strings on the fly
(`get_report_strings` → translate → `custom_strings`) while the code verifies
that the number placeholders survived translation, so the statistics stay exact.

Want your language built in? It's one dictionary in [i18n.py](../i18n.py). PRs welcome.

## Anonymous benchmark — what gets sent

**Opt-in only.** Nothing is ever sent without explicit consent.

If you consent, these five aggregates are sent, and this is everything:

```json
{
  "users_count": 40,
  "churned_rate": 0.30,
  "weekend_rate": 0.175,
  "regular_rate": 0.275,
  "aha_lift": 0.82
}
```

Never sent: user IDs, event logs, dates, your product's name, IP-based identifiers.

The backend is INSERT-only (row-level security) — submitted data cannot be read
back with the public key, and comparisons go through a function that returns
percentile statistics only. Verify it yourself: [benchmark.py](../benchmark.py),
about 60 lines.

## FAQ

**How do I analyze user behaviour for an early-stage product?**
Under ~1,000 users, skip the heavyweight analytics suites. Connect your database
or export three columns, then ask Claude to analyze it. Churn, weekend-only
users, and habit changes become visible in seconds.

**How do I find my aha moment?**
`find_aha_moments` scans every event and measures, per user, how their own
activity changed before vs after they first did that action — so frequency noise
(scrolling, popups) doesn't fool the ranking. The report aligns everyone on "day
zero" so you can see the habit change yourself.

**How is this different from Mixpanel / Amplitude / PostHog?**
Those are built for thousands of users and aggregate charts. This is built for
your first hundred: per-user visibility, running locally inside your coding
agent, no SDK, no signup, statistics computed by code and never by the LLM.
Graduate to the big tools later — this is the stage before them.
