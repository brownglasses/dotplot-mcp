# Dot Plot MCP

> See individual users, not aggregate charts.

**English** | [한국어](README.ko.md)

![report](.github/report_en.png)

DAU/MAU charts trend "up and to the right" as long as new users arrive — even
when nobody sticks. This MCP server implements
[YC's Dot Plot methodology](https://www.youtube.com/watch?v=e5-6rEwzxLs)
(David Lieb): until you have hundreds of users, the most informative dashboard
is **one row per user, one cell per day**.

**Design principle: code computes the numbers, AI only interprets them.**
Statistics never come from an LLM, so they are never wrong.

## What it does

```
1. Tracking audit   compare events in your code vs events in your data → find broken/missing tracking
2. Dot plot         every user's activity as dots — churn, weekend-only, core fans at a glance
3. Classification   used-once / weekend-only / almost-daily, automatically
4. Aha moments      scan every action for "what turns users into regulars"
5. Report           hand-drawn style HTML + plain-language insights → share as a link
6. Benchmark        (opt-in) compare your metrics with teams at your industry & stage
```

### 30-second demo

![demo](.github/demo.gif)

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/), and a 3-column CSV: `user_id, date, event`.

```bash
# Register with Claude Code
claude mcp add dotplot -- uv run --python 3.12 /path/to/dotplot-mcp/server.py

# No data yet? Try the sample
uv run sample_data.py   # generates events.csv (40 fake users)
uv run demo.py          # watch the whole pipeline run
```

Then ask Claude:

> "Analyze events.csv and find my aha moment"

Exporting from your own DB is one query:

```sql
SELECT user_id, created_at::date AS date, 'purchase' AS event FROM orders;
```

## Tools

| Tool | What it does |
|---|---|
| `describe_events` | Understand the data shape (always call first) |
| `dot_plot` | Text dot plot (◎ signup day, ● active day, custom marks) |
| `classify_users` | Automatic behavioral pattern classification |
| `find_aha_moments` | Scan all events for "regular-converting" actions |
| `audit_tracking` | Compare events in code vs data (find tracking gaps) |
| `generate_report` | Hand-drawn style HTML report + rule-based insights |
| `publish_report` | Host the report at a random URL, get a share link (Vercel) |
| `submit_benchmark` | Submit aggregates to the anonymous benchmark (explicit consent required) |
| `compare_benchmark` | Compare your metrics with percentiles of similar teams |

## Languages

Reports work in **any language**. English, 한국어, and 日本語 are built in;
for every other language the agent translates the report strings on the fly
(`get_report_strings` → translate → `custom_strings`), while the code validates
that number placeholders survive translation — so statistics stay exact.
Want your language built in? It's one dictionary in [i18n.py](i18n.py). PRs welcome.

See the same report in [English](.github/report_en.png) · [한국어](.github/report_ko.png) · [日本語](.github/report_ja.png).

## Anonymous benchmark — what gets sent

**Opt-in only.** Nothing is ever sent without explicit consent.

If you consent, these five aggregates are sent — and this is **everything**:

```json
{
  "users_count": 40,
  "churned_rate": 0.30,
  "weekend_rate": 0.175,
  "regular_rate": 0.275,
  "aha_lift": 0.82
}
```

Never sent: user IDs, event logs, dates, your service's name, IP-based identifiers.

The backend is INSERT-only (row-level security) — submitted data cannot be read
back with the public key, and comparisons go through a function that returns
percentile statistics only. Verify yourself: [benchmark.py](benchmark.py) (~60 lines).

## Architecture

```
analysis.py    all computation — pure Python, knows nothing about MCP (the brain)
server.py      thin shell exposing computations as MCP tools
report.py      HTML report rendering + rule-based insight sentences
benchmark.py   anonymous benchmark client
i18n.py        every user-facing sentence, per language
harness.py     run the whole pipeline end-to-end without an agent
sample_data.py sample data with planted patterns (for verifying the tool)
hosting/       Vercel project template for report hosting
```

## Why it's built this way

- **LLMs don't compute** — same data, same numbers, every time
- **Small samples withhold judgment** — groups under 5 users are excluded from aha candidates
- **Correlation ≠ causation** — every insight ships with a "verify with an experiment" warning
- **Vanity metrics blocked** — pick `open_app` as your value event and it tells you to pick again

## License

MIT
