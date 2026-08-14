# Set up Dotplot — MCP server + skills

You are an agent reading this on the user's behalf. Do the steps below, then
tell the user what they can now say. Ask before each command that changes their
machine.

Dotplot is per-user product analytics: one row per user, one dot per active day.
It finds the action that turns new users into regulars, shows where new users
leak out of onboarding, and writes a report — with every statistic computed by
Python, never by a model.

## Step 1 — the MCP server (required)

This is the engine. It needs [uv](https://docs.astral.sh/uv/) installed.

```bash
claude mcp add --scope user dotplot -- uvx dotplot-mcp
```

`--scope user` matters: without it the server is registered only for the
directory the command ran in, and "analyze my product" will do nothing
everywhere else.

Verify it connected:

```bash
claude mcp list | grep dotplot
```

If uv is missing, install it first: `curl -LsSf https://astral.sh/uv/install.sh | sh`

For Cursor, Windsurf, or another MCP client, add this to its MCP config instead:

```json
{ "mcpServers": { "dotplot": { "command": "uvx", "args": ["dotplot-mcp"] } } }
```

## Step 2 — the skills (optional, recommended)

The server computes; the skills carry the judgement — which action counts as
"value", when a number has too few users behind it to report, how to name an
event you'll live with for years. They become slash commands.

```bash
git clone --depth 1 https://github.com/brownglasses/dotplot-mcp /tmp/dotplot-setup \
  && mkdir -p ~/.claude/skills \
  && cp -r /tmp/dotplot-setup/skills/dotplot-* ~/.claude/skills/ \
  && rm -rf /tmp/dotplot-setup
```

That installs three commands:

| | |
|---|---|
| `/dotplot-analyze-product` | Find the data, pick the value event, produce the report |
| `/dotplot-add-tracking` | Read the code for missing logging, write it, set a return date |
| `/dotplot-whats-changed` | Compare with the previous report |

For Cursor or Codex, copy into `~/.cursor/skills/` or `~/.codex/skills/` instead.
The skills call the MCP server, so step 1 is required either way.

## Step 3 — tell the user what to say

Restart the client so it picks up the new server, then:

> **"Analyze my product"**

They don't need to prepare anything. You will find the data yourself: check for
`DOTPLOT_DB_URL`, a connection string in `.env`, or a database MCP that's already
connected. Most early products have no `events` table — that's expected. Their
ordinary tables are the event log:

```sql
SELECT user_id, created_at::date AS date, 'purchase' AS event FROM orders
UNION ALL
SELECT user_id, added_at::date, 'add_to_wishlist' FROM wishlist_items
```

If the product tracks nothing at all, say so plainly rather than producing an
empty report, and offer `/dotplot-add-tracking` instead — it reads the code for
the actions that should be logged and aren't, writes the logging, and tells them
how many days to wait before there's anything to analyze.

## Notes worth passing on

- **Nothing is uploaded.** The analysis runs on their machine. The data goes
  from their database to a file to the report and never passes through a model.
- **`publish_report` is the exception** — it puts the report on the public web
  at a random URL. Ask before running it.
- Reports come out in the user's language. English, 한국어, and 日本語 are built
  in; any other language is translated with the numbers verified intact.

Source: https://github.com/brownglasses/dotplot-mcp
