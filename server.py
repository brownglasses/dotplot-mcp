# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2.0"]
# ///
"""Dot Plot MCP 서버 — 얇은 껍데기.

계산은 전부 analysis.py가 하고, 여기서는 그걸 MCP 툴로 노출만 한다.
그다음 '그래서 뭘 해야 하는지' 해석은 Claude가 한다. ← 여기가 상품

이 파일의 docstring과 반환값은 영어로 쓴다. 에이전트가 읽는 글이고,
사용자는 전 세계에 있기 때문이다. 코드 주석은 한국어 — 그건 우리가 읽는 것이다.
사람에게 보일 문장은 여기 두지 말고 i18n.py로 보낼 것.
"""
from datetime import date, timedelta

from mcp.server import MCPServer

import analysis

mcp = MCPServer("dotplot")


def _prepare(csv_path: str, value_event: str):
    """모든 분석 툴의 공통 앞단: 로드 → value_event 검증 → 유저 구조 만들기.

    검증을 여기 한 곳에 모아두는 이유: 오타난 이벤트 이름이 통과하면
    '이탈률 100%, 리텐션 0%'라는 그럴듯한 거짓 리포트가 나간다.
    """
    events = analysis.load_events(csv_path)
    analysis.check_value_event(events, value_event)
    users = analysis.build_users(events, value_event)
    today = max(e["date"] for e in events)
    return events, users, today


@mcp.tool()
def analyze(
    csv_path: str | None = None,
    value_event: str | None = None,
    lang: str = "en",
    output_path: str = "dotplot_report.html",
) -> dict:
    """START HERE. Event data in, finished report out, one call.

    Use this whenever the user asks anything general — "analyze my product",
    "how are my users doing", "find my aha moment". The other tools are parts;
    this is the whole thing. Only reach for them when the user asks for one
    specific number ("just show me retention").

    It picks a value event, draws the dot plot, finds the aha moment, builds the
    funnel and retention curve, and writes the HTML report — then tells you what
    it found so you can say it out loud.

    csv_path: a CSV with user_id, date, event (platform optional).
      No CSV yet? Call with no arguments and follow the instructions you get
      back — for a project with a database you will explore its schema and turn
      ordinary business tables (orders, sessions, posts) into events with
      load_from_db. Most early products have no events table; that is expected.

    value_event: the action that means "this user got real value".
      Leave it out and the code picks the candidate most users repeat. Pass it
      yourself when you have read the codebase and know better — you can tell
      `purchase` from `view_item` and the code cannot. The result always names
      what was chosen and what else was available, so you can call again with a
      different one if the choice looks wrong.

    lang: the user's language. en/ko/ja are built in; for any other language
      call get_report_strings, translate, and use generate_report directly.
    """
    if not csv_path:
        return {
            "status": "need_data",
            "what_to_do": [
                "1. Look for a database: is DOTPLOT_DB_URL set? Is there a connection "
                "string in .env, or a Postgres/Supabase MCP already connected?",
                "2. Read the schema. You are looking for tables that record things "
                "users did — orders, sessions, posts, messages, subscriptions. "
                "An 'events' table is nice but rare at this stage.",
                "3. Turn those tables into events with load_from_db, one SELECT per "
                "table joined by UNION ALL: "
                "SELECT user_id, created_at::date AS date, 'purchase' AS event FROM orders "
                "UNION ALL SELECT user_id, added_at::date, 'add_to_wishlist' FROM wishlist_items",
                "4. Call analyze again with the CSV it wrote.",
                "If there is no database and nothing is tracked, say so plainly — this "
                "tool cannot help yet. Offer to add event logging instead: find the "
                "handlers for the product's core actions and use audit_tracking.",
            ],
        }

    events = analysis.load_events(csv_path)
    ranked = analysis.rank_value_events(events)

    if value_event is None:
        best = next((r for r in ranked if r["usable"]), None)
        if best is None:
            return {
                "status": "no_value_event",
                "candidates": ranked,
                "what_to_do": (
                    "Nothing in this data looks like a value event: every action is "
                    "either a vanity metric, done by too few users, or never repeated. "
                    "That is a tracking problem, not a product problem. Tell the user "
                    "which core actions are not being recorded and offer to add logging "
                    "(audit_tracking has the procedure)."
                ),
            }
        value_event = best["event"]
        chosen_because = (
            f"{best['coverage']:.0%} of users did it, {best['days_per_user']} days each "
            "on average — the most repeated action in the data that isn't a vanity metric"
        )
    else:
        analysis.check_value_event(events, value_event)
        chosen_because = "you passed it explicitly"

    users = analysis.build_users(events, value_event)
    today = max(e["date"] for e in events)
    buckets = analysis.classify_users(users, today)
    aha = analysis.find_aha_moments(events, users, value_event, today)
    funnel = analysis.onboarding_funnel(users, today)
    retention = analysis.retention_curve(users, today)

    generate_report(csv_path, value_event, output_path=output_path, lang=lang)

    import re

    import report as report_mod

    headline = [
        re.sub(r"</?b>", "", line)
        for line in report_mod.build_insights(len(users), buckets, aha, lang=lang)
    ]
    top = analysis.top_aha(aha)

    return {
        "status": "ok",
        "report": output_path,
        "value_event": {
            "chosen": value_event,
            "why": chosen_because,
            "others_available": [r["event"] for r in ranked if r["event"] != value_event],
        },
        "headline": headline,
        "aha_moment": {
            "event": top["event"],
            "regulars_who_did_it": top["did_regular_rate"],
            "regulars_who_did_not": top["not_regular_rate"],
            "activity_change_after": top["behavior_change"],
        } if top else None,
        "users": {"total": len(users), **{k: len(v) for k, v in buckets.items()}},
        "funnel": funnel,
        "retention": retention,
        "next": [
            f"Show the user the report at {output_path} and read the headline out loud.",
            "The aha moment is a correlation, not a cause — suggest testing it in "
            "onboarding rather than stating it as fact.",
            "Offer publish_report only if they want a shareable link (it goes on the web).",
            "If the value event looks wrong, call analyze again with value_event set.",
        ],
    }


@mcp.tool()
def describe_events(csv_path: str) -> dict:
    """Shape of an event CSV: date range, user count, events by type.

    Mostly useful when you want to look before choosing a value event yourself.
    For a normal "analyze my product" request call analyze instead — it does
    this step and everything after it.
    """
    events = analysis.load_events(csv_path)
    counts: dict[str, int] = {}
    for e in events:
        counts[e["event"]] = counts.get(e["event"], 0) + 1
    dates = [e["date"] for e in events]
    ranked = dict(sorted(counts.items(), key=lambda x: -x[1]))
    return {
        "users": len({e["user_id"] for e in events}),
        "events_total": len(events),
        "event_types": ranked,
        "date_range": [min(dates).isoformat(), max(dates).isoformat()],
        # value_event 후보를 코드가 미리 걸러준다 — 허영 지표는 애초에 거부되므로
        "value_event_candidates": [e for e in ranked if not analysis.is_vanity(e)],
        "rejected_as_vanity": [e for e in ranked if analysis.is_vanity(e)],
        "hint": "A value event means 'this user got something real'. Vanity "
                "metrics are rejected by the code, not left to your judgement.",
    }


@mcp.tool()
def dot_plot(
    csv_path: str,
    value_event: str,
    mark_events: dict[str, str] | None = None,
    weeks: int = 6,
    lang: str = "en",
) -> str:
    """Text dot plot: one row per user, one cell per day.

    ◎ first active day, ● value event, · nothing. mark_events puts a letter on
    other actions, e.g. {"create_playlist": "P"}.
    """
    events, users, _ = _prepare(csv_path, value_event)
    start = min(e["date"] for e in events)
    return analysis.render_dot_plot(users, start, weeks * 7, mark_events, lang=lang)


@mcp.tool()
def classify_users(csv_path: str, value_event: str, lang: str = "en") -> dict:
    """Sort users by behaviour: churned (used once, never returned),
    weekend_only, regular (almost daily), casual.

    lang sets the human-readable labels (en/ko/ja); the keys stay in English.
    """
    from i18n import t

    _, users, today = _prepare(csv_path, value_event)
    buckets = analysis.classify_users(users, today)
    return {
        k: {"label": t(lang, f"bucket.{k}"), "count": len(v), "users": v}
        for k, v in buckets.items()
    }


@mcp.tool()
def find_aha_moments(csv_path: str, value_event: str) -> dict:
    """Scan every action for the one that turns users into regulars.

    Ranked by behaviour_change — how much a user's own activity rose after they
    first did it — because comparing groups (lift) rewards actions that frequent
    users happen to do. Tell the user this is correlation, not cause.
    """
    events, users, today = _prepare(csv_path, value_event)
    return {
        "candidates": analysis.find_aha_moments(events, users, value_event, today),
        "caution": "Correlation, not cause. The way to find out is to put the "
                   "action in onboarding and A/B test it.",
    }


@mcp.tool()
def audit_tracking(code_events: list[str], csv_path: str) -> dict:
    """Compare the events logged in the code against the events in the data.

    This is also the tool for a project that tracks nothing yet — there is no
    data to analyse, but there is code to read.

    How to use it:
    1. Search the codebase for logging calls yourself. Common shapes:
       logEvent(...), track(...), analytics.capture(...), posthog.capture(...),
       gtag('event', ...), mixpanel.track(...)
    2. Pass the event names you found as code_events.
    3. Read the result:
       - in_code_never_fired  logging is broken, or nobody uses that feature
       - in_data_not_in_code  dead code, or your search missed it (look again)
    4. Then find what has no logging at all — button handlers and core actions
       that should be recorded and aren't. That gap won't appear in either list,
       and it is usually the important one.
    5. Prescribe, don't just report. For each hole write the one line of logging
       that belongs in that file, in that function, matching the surrounding
       style, show it, and ask whether to add it. Follow the project's existing
       naming (follow_artist if it is snake_case, followArtist if camelCase).
    """
    events = analysis.load_events(csv_path)
    data_events = {e["event"] for e in events}
    return analysis.audit_tracking(code_events, data_events)


@mcp.tool()
def get_report_strings() -> dict:
    """Every sentence the report can contain, in English, for translation.

    For a language other than en/ko/ja:
    1. call this,
    2. translate the values — leave {n}, {rate_did} and every other brace
       placeholder exactly as they are, that is where the numbers go,
    3. pass the result to generate_report as custom_strings with lang="custom".
    The code checks the placeholders survived, so the statistics stay exact.
    """
    from i18n import STRINGS

    return STRINGS["en"]


@mcp.tool()
def generate_report(
    csv_path: str,
    value_event: str,
    output_path: str = "dotplot_report.html",
    mark_events: dict[str, str] | None = None,
    mark_labels: dict[str, str] | None = None,
    max_users: int = 20,
    weeks: int = 4,
    lang: str = "en",
    custom_strings: dict[str, str] | None = None,
) -> str:
    """Write the HTML dot plot report — readable in three seconds, made to share
    with a team or an investor.

    analyze calls this for you. Use it directly when you need to control the
    marks, the window, or a language that isn't built in.

    Marks on other actions:
    - default: the top aha events are picked automatically (behaviour change
      of 30 points or more, at most two, so the report stays quiet no matter
      how many event types exist)
    - your own: mark_events={"create_playlist": "P"}, described by mark_labels
    - none at all: mark_events={}

    Language: match the conversation. lang="en"|"ko"|"ja" are built in; for any
    other language translate get_report_strings() and pass it as custom_strings
    with lang="custom". Never translate the {brace} placeholders.
    """
    import report as report_mod

    if custom_strings:
        from i18n import register_custom

        bad = register_custom(custom_strings)
        lang = "custom"
        if bad:
            return f"Translation problem — fix these keys and call again: {bad}"

    events, users, today = _prepare(csv_path, value_event)
    start = min(e["date"] for e in events)
    subset = dict(sorted(users.items(), key=lambda kv: kv[1].signup)[:max_users])
    # 인사이트는 표에 보이는 일부가 아니라 전체 유저 기준으로 계산한다
    buckets = analysis.classify_users(users, today)
    aha_results = analysis.find_aha_moments(events, users, value_event, today)

    if mark_events is None:
        # 자동 선별: 전/후 행동 변화가 뚜렷한 상위 2개만 — 잡음 이벤트는 그리지 않는다
        mark_events, auto_labels = {}, {}
        used_letters: set[str] = set()
        for c in aha_results:
            if (c["behavior_change"] or 0) < analysis.AHA_MIN_BEHAVIOR_CHANGE:
                continue
            letter = next(
                (ch.upper() for ch in c["event"] if ch.isalpha() and ch.upper() not in used_letters),
                "*",
            )
            used_letters.add(letter)
            mark_events[c["event"]] = letter
            auto_labels[c["event"]] = f"{letter} = {c['event']}"
            if len(mark_events) == 2:
                break
        mark_labels = {**auto_labels, **(mark_labels or {})}

    labels = {ev: lbl.split("=")[-1].strip() for ev, lbl in (mark_labels or {}).items()}
    insights = report_mod.build_insights(len(users), buckets, aha_results, labels, lang=lang)
    funnel = analysis.onboarding_funnel(users, today)
    retention = analysis.retention_curve(users, today)

    # 히스토리: 스냅샷 자동 저장 + 지난번 대비 카드
    import history as hist_mod

    snap = hist_mod.make_snapshot(users, value_event, today)
    prev = hist_mod.previous_snapshot(snap)
    hist_mod.append_snapshot(snap)
    history_card = None
    if prev:
        history_card = {"date": prev["data_end"], "rows": hist_mod.diff(prev, snap)}
    # 아하 모먼트 카드: 1위 후보를 '한 날 = 0일' 정렬 그림으로
    aha_card = None
    top = analysis.top_aha(aha_results)
    if top and top["event"] in mark_events:
        ev = top["event"]
        doers = []
        for u in users.values():
            first = min((d for d, evs in u.special_days.items() if ev in evs), default=None)
            if first is None:
                continue
            offsets = {(d - first).days for d in u.value_days if -14 <= (d - first).days <= 14}
            doers.append({"id": u.user_id, "offsets": offsets, "after": len([o for o in offsets if o > 0])})
        doers.sort(key=lambda r: -r["after"])
        palette_color = "#e05c26"
        aha_card = {
            "event": ev,
            "letter": mark_events[ev],
            "color": palette_color,
            "did_count": top["did_count"],
            "did_rate": top["did_regular_rate"],
            "not_count": top["not_count"],
            "not_rate": top["not_regular_rate"],
            "rows": doers[:7],
        }

    # 나머지 이벤트는 범례에서 딸깍으로 켤 수 있게 (아하 순위 순, 최대 6개)
    extra_events = [c["event"] for c in aha_results if c["event"] not in mark_events][:6]
    html = report_mod.render_html_report(
        subset, start, weeks * 7, today,
        mark_events=mark_events, mark_labels=mark_labels, extra_events=extra_events,
        insights=insights, aha_card=aha_card, history=history_card, funnel=funnel, retention=retention, lang=lang,
    )
    with open(output_path, "w") as f:
        f.write(html)
    return f"Report written to {output_path} ({len(subset)} users, {weeks} weeks)"


@mcp.tool()
def onboarding_funnel(csv_path: str, value_event: str) -> dict:
    """Onboarding funnel: signup -> first value -> came back -> still active.

    Answers where new users leak. A large median_days_to_value means friction
    between signing up and getting anything out of the product.
    """
    _, users, today = _prepare(csv_path, value_event)
    return analysis.onboarding_funnel(users, today)


@mcp.tool()
def retention_curve(csv_path: str, value_event: str, max_weeks: int = 6) -> list:
    """Weekly retention: share of users with a value event in week N.

    Only users old enough to have reached week N count toward it, and weeks with
    fewer than five of them are dropped rather than reported as noise. Where the
    curve flattens is the retention that holds.
    """
    _, users, today = _prepare(csv_path, value_event)
    return analysis.retention_curve(users, today, max_weeks)


@mcp.tool()
def load_from_db(query: str, output_csv: str = "events.csv", db_url: str | None = None) -> dict:
    """Pull events out of the project's database into a CSV.

    How to use it:
    1. The connection string comes from DOTPLOT_DB_URL by default. Tell the user
       to export it — never ask them to paste a password into the chat:
       export DOTPLOT_DB_URL="postgresql://readonly:...@host:5432/db"
       (Supabase: Dashboard > Settings > Database > Connection string)
    2. Read the schema first (information_schema), find the tables that record
       what users did, and shape them into user_id, date, event. Most products
       have no events table — ordinary business tables are the event log:
       SELECT user_id::text, created_at::date AS date, 'purchase' AS event FROM orders
       Combine several actions with UNION ALL.
    3. Only SELECT runs; anything else is refused. Recommend a read-only role.

    Supports postgresql:// (Supabase, RDS, Neon) and sqlite:///path for testing.
    """
    import os

    url = db_url or os.environ.get("DOTPLOT_DB_URL")
    if not url:
        return {"error": "No database URL. Ask the user to set DOTPLOT_DB_URL."}

    q = query.strip().rstrip(";")
    if not q.lower().startswith(("select", "with")) or ";" in q:
        return {"error": "Only a single SELECT statement can be run."}

    if url.startswith("sqlite:///"):
        import sqlite3

        conn = sqlite3.connect(url[len("sqlite:///"):])
        try:
            cur = conn.execute(q)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        finally:
            conn.close()
    elif url.startswith(("postgresql://", "postgres://")):
        try:
            import psycopg
        except ImportError:
            return {"error": "psycopg is required: uv pip install 'psycopg[binary]'"}
        with psycopg.connect(url, options="-c default_transaction_read_only=on") as conn:
            with conn.cursor() as cur:
                cur.execute(q)
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
    else:
        return {"error": "Supported URLs: postgresql://... or sqlite:///..."}

    required = {"user_id", "date", "event"}
    if not required.issubset(set(cols)):
        return {"error": f"The query must return {sorted(required)}. It returned: {cols}"}

    import csv as _csv

    with open(output_csv, "w", newline="") as f:
        w = _csv.writer(f)
        has_platform = "platform" in cols
        w.writerow(["user_id", "platform", "date", "event"])
        idx = {c: i for i, c in enumerate(cols)}
        for r in rows:
            w.writerow([
                r[idx["user_id"]],
                r[idx["platform"]] if has_platform else "unknown",
                str(r[idx["date"]])[:10],
                r[idx["event"]],
            ])
    return {"saved": output_csv, "rows": len(rows), "next": "Call analyze with this CSV."}


@mcp.tool()
def history_compare(csv_path: str, value_event: str) -> dict:
    """Compare today's numbers with the last analysis of the same data.

    Snapshots are saved to ./.dotplot/history.json every time a report is made.
    Only snapshots of the same dataset are compared, so the first run of a new
    project has nothing to compare against — say so rather than implying zero
    change.
    """
    import history as hist_mod

    _, users, today = _prepare(csv_path, value_event)
    snap = hist_mod.make_snapshot(users, value_event, today)
    prev = hist_mod.previous_snapshot(snap)
    if not prev:
        return {"current": snap, "note": "First snapshot of this dataset — "
                "nothing to compare yet. Changes show from the next analysis on."}
    return {"previous_date": prev["data_end"], "current": snap, "changes": hist_mod.diff(prev, snap)}


@mcp.tool()
def find_similar_cases(csv_path: str, value_event: str, industry: str | None = None) -> dict:
    """Find companies that hit the same problem and what they changed.

    A small library curated from public material — YC talks, First Round, founder
    interviews. When you pass a case on:
    - explain matched_on, so the user knows why it came up
    - cite the source, and say the figures are second-hand
    - offer to apply the fix to their code (e.g. move the aha action into
      onboarding)
    industry: b2c|b2b|commerce|content|social|tool|game|other — a match in the
    same industry ranks higher.
    """
    import cases as cases_mod

    events, users, today = _prepare(csv_path, value_event)
    tags = cases_mod.diagnose_tags(users, events, value_event, today)
    matched = cases_mod.match_cases(tags, industry)
    return {
        "your_symptoms": sorted(tags),
        "similar_cases": matched,
        "caution": "Curated from public material. Their context differs from "
                   "yours — treat it as a hypothesis to test, not a recipe.",
    }


HOSTING_DIR = "hosting"  # server.py 옆의 Vercel 프로젝트 폴더 (저장소를 클론한 경우)

# uvx/pip로 설치하면 hosting/이 같이 안 깔린다 — 그때 쓸 최소 Vercel 프로젝트.
# 무작위 주소 + noindex라는 프라이버시 속성이 여기 담겨 있으므로 반드시 함께 만든다.
_VERCEL_JSON = """{
  "cleanUrls": false,
  "headers": [
    {
      "source": "/r/(.*)",
      "headers": [
        { "key": "X-Robots-Tag", "value": "noindex, nofollow" },
        { "key": "Cache-Control", "value": "public, max-age=60" }
      ]
    }
  ]
}
"""


def _hosting_dir():
    """Vercel 프로젝트 폴더를 찾거나 만든다.

    1순위: 모듈 옆 hosting/ (저장소 클론 — 랜딩페이지까지 포함된 원본)
    2순위: ./.dotplot/hosting/ (uvx 설치 — 최소 설정을 즉석에서 생성)
    """
    from pathlib import Path

    bundled = Path(__file__).parent / HOSTING_DIR
    if (bundled / "vercel.json").exists():
        return bundled

    local = Path(".dotplot") / "hosting"
    local.mkdir(parents=True, exist_ok=True)
    vercel_json = local / "vercel.json"
    if not vercel_json.exists():
        vercel_json.write_text(_VERCEL_JSON)
    return local


@mcp.tool()
def publish_report(html_path: str) -> dict:
    """Host the report and return a shareable link.

    ASK THE USER FIRST. This puts their product's numbers on the public web.
    Only run it when they have said they want a link.

    The report goes to a random path in a Vercel project and is deployed with
    `vercel deploy --prod`. The random path plus a noindex header means only
    someone with the link can reach it and search engines won't list it — but it
    is still the open internet. Requires the vercel CLI to be logged in. To take
    one down, delete the file under r/ and deploy again.
    """
    import re
    import secrets
    import shutil
    import subprocess
    from pathlib import Path

    path = Path(html_path).resolve()
    if not path.exists():
        return {"error": f"No such file: {path}"}

    hosting = _hosting_dir()
    (hosting / "r").mkdir(parents=True, exist_ok=True)

    report_id = secrets.token_hex(6)
    dest = f"r/{report_id}.html"
    shutil.copy(path, hosting / dest)

    r = subprocess.run(
        ["vercel", "deploy", "--prod", "--yes"],
        capture_output=True, text=True, cwd=hosting,
    )
    if r.returncode != 0:
        return {"error": f"Deploy failed: {r.stderr.strip()[-500:]}"}

    # 고정 도메인 = stderr의 "Aliased https://프로젝트명.vercel.app" 줄
    import json as _json

    base = None
    m = re.search(r"Aliased\s+(https://\S+)", r.stderr)
    if m:
        base = m.group(1)
    if not base:  # 별칭을 못 찾으면 배포 고유 URL로라도
        try:
            base = _json.loads(r.stdout)["deployment"]["url"]
        except (ValueError, KeyError):
            return {"error": f"Deployed, but the URL could not be read: {r.stdout[-300:]}"}
    return {
        "share_url": f"{base}/{dest}",
        "how_to_remove": f"Delete {hosting}/{dest} and deploy again",
        "note": "Random path + noindex — reachable only with the link, "
                "but it is on the public web.",
    }


@mcp.tool()
def submit_benchmark(
    csv_path: str, value_event: str, industry: str, stage: str, consent: bool = False
) -> dict:
    """Submit five aggregate numbers to the anonymous benchmark. Opt-in.

    Set consent=True only after the user has explicitly agreed. When you ask,
    show them exactly what leaves the machine — user count, churn rate, weekend
    rate, regular rate, aha lift, and nothing else. No user IDs, no event log,
    no product name.

    industry: b2c|b2b|commerce|content|social|tool|game|other
    stage: pre_launch|under_100_users|under_1k_users|over_1k_users
    """
    import benchmark as bench

    if not consent:
        return {"error": "Consent required. Show the user what would be sent, "
                         "and call again with consent=True only if they agree."}
    if industry not in bench.INDUSTRIES or stage not in bench.STAGES:
        return {"error": f"industry must be one of {bench.INDUSTRIES}, "
                         f"stage one of {bench.STAGES}"}

    events, users, today = _prepare(csv_path, value_event)
    agg = bench.compute_aggregates(events, users, value_event, today)
    bench.submit(agg, industry, stage)
    return {"submitted": agg, "note": "Nothing beyond these numbers was sent."}


@mcp.tool()
def compare_benchmark(csv_path: str, value_event: str, industry: str, stage: str) -> dict:
    """Compare your numbers with percentiles from teams at the same industry
    and stage.

    Below ten teams the percentiles mean nothing — say so plainly instead of
    reporting them.
    """
    import benchmark as bench

    events, users, today = _prepare(csv_path, value_event)
    mine = bench.compute_aggregates(events, users, value_event, today)
    peers = bench.fetch(industry, stage)

    result = {"yours": mine, "peers": peers}
    sample = (peers or {}).get("sample_size") or 0
    if sample < 10:
        result["caution"] = (f"Only {sample} teams in this group — not enough to "
                             "compare against yet. Don't present it as a benchmark.")
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
