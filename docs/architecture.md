# How it's built

```
analysis.py    all computation — pure Python, knows nothing about MCP (the brain)
server.py      thin shell exposing computations as MCP tools and prompts
report.py      HTML report rendering + rule-based insight sentences
history.py     snapshots, so "since last time" has something to compare against
cases.py       curated library of documented retention fixes
benchmark.py   anonymous benchmark client
i18n.py        every user-facing sentence, per language
harness.py     run the whole pipeline end-to-end without an agent
               (add --slow for the paced, coloured version used to record the GIF)
sample_data.py sample data with patterns planted in it, for verifying the tool
hosting/       Vercel project template for report hosting
tests/         the paths a demo never takes — see below
```

## The rules the code follows

**Code computes, AI interprets.** `analysis.py` never imports anything from MCP
and never asks a model for a number. Given the same data it returns the same
numbers, every time. What the agent adds is the part models are good at: reading
the codebase, knowing that `purchase` means something and `view_item` doesn't,
and saying what to do about it.

**One definition per idea.** "Regular", the aha threshold, and how long a user
must be watched before judging them each live in exactly one constant. Every
bug this project has shipped came from the same shape — the same rule written
down in two places, drifting apart until a report contradicted itself.

**Small samples withhold judgment.** Groups under five are dropped from aha
candidates; retention weeks with fewer than five eligible users are cut rather
than reported. A confident number computed from four people is worse than no
number.

**Refuse rather than guess.** A value event that isn't in the data, a vanity
metric, an ambiguous date — all rejected with a message saying what to do
instead. The failure mode this protects against isn't a crash; it's a report
that looks right and isn't.

## Language

What a machine reads is English: tool descriptions, dict keys, error messages.
What a person reads goes through `i18n.py`. Code comments are Korean, because
that's who reads them.

## Tests

The test suite targets exactly the paths `harness.py` can't reach — it always
runs a 4-column sample CSV through a valid value event from inside the repo, so
it looks green while whole categories of bug go unexercised. The tests cover:

- the 3-column input the README documents (the sample always writes 4)
- value events that are typos or vanity metrics (the sample is always valid)
- **the built wheel installed into an empty venv** (the repo always has every
  module importable, which is how a missing packaging entry shipped once)
- files exported by other database tools, in four formats
- history comparing only snapshots of the same dataset
- reports escaping user data before it becomes markup

The wheel test copies the source to a temp directory before building, because
setuptools will happily copy whatever is left in `build/lib` into the wheel
regardless of the manifest — so building in a working tree hides exactly the
mistake the test exists to catch.

## Releasing

Push a tag; `release.yml` runs tests → PyPI → MCP registry, each gated on the
one before, and verifies PyPI actually serves the version before registering it.
Done by hand, PyPI can fail while the registry goes on to advertise a version
that doesn't exist.

```bash
git tag v0.1.3 && git push origin v0.1.3
```

The version lives in four places (tag, `pyproject.toml`, and twice in
`server.json`); the workflow refuses to publish unless all four agree.
