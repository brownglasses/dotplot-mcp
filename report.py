"""HTML 리포트 생성 — YC 손그림 도트 플롯 스타일. 다국어 지원.

디자인 원칙 (참고 이미지 그대로):
  - 공책 종이 느낌: 흰 바탕 + 옅은 점 패턴, 손글씨 폰트
  - 검은 얇은 격자, 주말 세로줄은 살구색으로 통째로 칠함
  - 파란 점 = 활동, ◎ 고리 = 가입일, 주황 점 = 주말에만 쓰는 유저
  - 제일 중요한 것: 설명 없이도 3초 안에 읽혀야 한다
언어: lang 인자로 결정 (en/ko/ja/...) — 문장은 전부 i18n.py에서 온다.
"""
from __future__ import annotations

from datetime import date, timedelta
from html import escape

from analysis import UserRow, classify_users, top_aha
from i18n import t

WEEKDAY_EN = ["M", "T", "W", "TH", "F", "SA", "S"]


def esc(value) -> str:
    """유저 데이터(유저 ID, 이벤트 이름, 라벨)를 HTML에 넣기 전 반드시 통과시킨다.

    리포트는 publish_report로 공개 URL에 올라간다 — 남의 DB에서 온 문자열이
    그대로 마크업이 되면 안 된다.
    """
    return escape(str(value), quote=True)

# 손글씨 폰트: 라틴은 Patrick Hand, 한글 Gaegu, 일어 Yomogi
FONTS = {
    "en": ("Patrick+Hand", "'Patrick Hand'"),
    "ko": ("Gaegu:wght@400;700", "'Gaegu','Patrick Hand'"),
    "ja": ("Yomogi", "'Yomogi','Patrick Hand'"),
}


def build_insights(
    all_users_count: int,
    buckets: dict[str, list[str]],
    aha_results: list[dict],
    event_labels: dict[str, str] | None = None,
    lang: str = "en",
) -> list[str]:
    """계산된 숫자를 쉬운 문장으로 바꾼다 — 전부 규칙 기반, LLM 없음.
    과장 금지: 항상 숫자를 병기하고, 확실할 때만 말한다."""
    labels = event_labels or {}
    out = []

    top = top_aha(aha_results)
    if top:
        out.append(t(lang, "insight.aha",
            name=esc(labels.get(top["event"], top["event"])),
            did=top["did_count"],
            rate_did=f"{top['did_regular_rate']:.0%}",
            rate_not=f"{top['not_regular_rate']:.0%}",
        ))

    churned = buckets.get("churned", [])
    if len(churned) / all_users_count >= 0.25:
        out.append(t(lang, "insight.churn",
            total=all_users_count, churned=len(churned),
            pct=f"{len(churned)/all_users_count:.0%}",
        ))

    weekend = buckets.get("weekend_only", [])
    if len(weekend) >= 3:
        out.append(t(lang, "insight.weekend", n=len(weekend)))

    if not out:
        out.append(t(lang, "insight.none"))
    return out


def render_html_report(
    users: dict[str, UserRow],
    start: date,
    days: int,
    today: date,
    mark_events: dict[str, str] | None = None,   # {"create_playlist": "P", "share": "S"} — 기본 켜짐
    mark_labels: dict[str, str] | None = None,   # {"create_playlist": "P = created a playlist"}
    extra_events: list[str] | None = None,       # 범례에서 딸깍으로 켤 수 있는 추가 이벤트들
    insights: list[str] | None = None,
    aha_card: dict | None = None,  # {"event","letter","color","did_count","did_rate","not_count","not_rate","rows":[{"id","offsets":set}]}
    history: dict | None = None,   # {"date": "...", "rows": [{key,before,after,delta,good}]}
    funnel: dict | None = None,
    retention: list[dict] | None = None,
    lang: str = "en",
) -> str:
    buckets = classify_users(users, today)
    weekend_only = set(buckets.get("weekend_only", []))

    mark_events = mark_events or {}
    mark_labels = mark_labels or {}
    used = set(mark_events.values())
    extra_marks: dict[str, str] = {}
    for ev in extra_events or []:
        if ev in mark_events:
            continue
        letter = next((ch.upper() for ch in ev if ch.isalpha() and ch.upper() not in used), "*")
        used.add(letter)
        extra_marks[ev] = letter
    all_marks = {**mark_events, **extra_marks}  # 순서 = 우선순위
    palette = ["#e05c26", "#7b5cd6", "#0f8a6d", "#d4537e", "#b8860b", "#4a6fa5", "#8a5a44", "#5e7a1e"]
    mark_colors = {ev: palette[i % len(palette)] for i, ev in enumerate(all_marks)}

    dates = [start + timedelta(days=i) for i in range(days)]
    weekdays = t(lang, "weekdays").split(",") if lang != "en" else WEEKDAY_EN

    head = "<tr><th></th>" + "".join(
        f'<th class="{"we" if d.weekday() >= 5 else ""}">{weekdays[d.weekday()]}</th>'
        for d in dates
    ) + "</tr>"

    body = []
    for u in sorted(users.values(), key=lambda x: x.signup):
        cells = []
        for d in dates:
            klass = "we" if d.weekday() >= 5 else ""
            day_specials = u.special_days.get(d, set())
            base = ""
            if d in u.value_days:
                base = "ring" if d == u.signup else ("orange" if u.user_id in weekend_only else "dot")
            hit = next((ev for ev in mark_events if ev in day_specials), None)
            if hit:
                inner = f'<span class="aha" style="background:{mark_colors[hit]}">{esc(mark_events[hit])}</span>'
            elif base:
                inner = f'<span class="{base}"></span>'
            else:
                inner = ""
            present = [ev for ev in all_marks if ev in day_specials]
            attrs = f' data-ev="{esc("|".join(present))}" data-base="{base}"' if present else ""
            cells.append(f'<td class="{klass}"{attrs}>{inner}</td>')
        body.append(f'<tr><td class="name">{esc(u.user_id.upper())}</td>{"".join(cells)}</tr>')

    summary = "".join(
        f'<li>{t(lang, "report.glance_item", n=len(ids), label=t(lang, f"bucket.{key}"))}</li>'
        for key, ids in sorted(buckets.items(), key=lambda x: -len(x[1]))
    )

    import json as _json

    chips = []
    for ev, letter in all_marks.items():
        on = ev in mark_events
        chips.append(
            f'<button class="chip{"" if on else " off"}" data-toggle="{esc(ev)}">'
            f'<span class="aha lg" style="background:{mark_colors[ev]}">{esc(letter)}</span> '
            f'{esc(mark_labels.get(ev, ev))}</button>'
        )
    aha_legend = "".join(chips)
    # <script> 안에 들어가므로 '<'를 유니코드 이스케이프해서 태그가 조기 종료되지 않게 한다
    marks_js = _json.dumps({
        ev: {"l": letter, "c": mark_colors[ev], "on": ev in mark_events}
        for ev, letter in all_marks.items()
    }).replace("<", "\\u003c")

    aha_html = ""
    if aha_card and aha_card.get("rows"):
        SPAN = 14  # 전후 14일
        color = aha_card["color"]
        head_cells = []
        for off in range(-SPAN, SPAN + 1):
            label = t(lang, "aha.day0") if off == 0 else (f"{off:+d}" if abs(off) in (7, 14) else "")
            head_cells.append(f'<div class="acell ahead{" azero" if off == 0 else ""}">{label}</div>')
        rows_html = []
        for row in aha_card["rows"]:
            cells = []
            for off in range(-SPAN, SPAN + 1):
                if off == 0:
                    cells.append(f'<div class="acell azero"><span class="aha sm" style="background:{color}">{esc(aha_card["letter"])}</span></div>')
                elif off in row["offsets"]:
                    cells.append('<div class="acell"><span class="adot"></span></div>')
                else:
                    cells.append('<div class="acell"><span class="aempty">·</span></div>')
            rows_html.append(f'<div class="arow"><div class="aname">{esc(row["id"].upper())}</div>{"".join(cells)}</div>')
        did_pct, not_pct = aha_card["did_rate"], aha_card["not_rate"]
        bars = (
            f'<div class="frow"><div class="flabel">{t(lang, "aha.did_bar", n=aha_card["did_count"])}</div>'
            f'<div class="fbar"><div class="ffill" style="width:{max(did_pct*100,2):.0f}%;background:{color}"></div></div>'
            f'<div class="fnum"><b>{did_pct:.0%}</b> <small>{t(lang, "aha.regulars")}</small></div></div>'
            f'<div class="frow"><div class="flabel">{t(lang, "aha.not_bar", n=aha_card["not_count"])}</div>'
            f'<div class="fbar"><div class="ffill" style="width:{max(not_pct*100,2):.0f}%;background:#c9c6bc"></div></div>'
            f'<div class="fnum">{not_pct:.0%} <small>{t(lang, "aha.regulars")}</small></div></div>'
        )
        aha_html = (
            f'<div class="card ahacard" style="border-color:{color}">'
            f'<h2>{t(lang, "aha.title", name=esc(aha_card["event"]))}</h2>'
            f'<p class="note" style="margin:0 0 10px">{t(lang, "aha.subtitle")}</p>'
            f'<div class="agrid"><div class="arow"><div class="aname"></div>{"".join(head_cells)}</div>{"".join(rows_html)}</div>'
            f'<div style="margin-top:16px">{bars}</div>'
            f'<p class="note">{t(lang, "aha.footer")}</p></div>'
        )

    history_card = ""
    if history and history.get("rows"):
        hrows = []
        for r in history["rows"]:
            fmt = (lambda v: f"{v:.0%}") if "rate" in r["key"] or "retention" in r["key"] else str
            arrow = "▲" if r["delta"] > 0 else ("▼" if r["delta"] < 0 else "—")
            klass = "up" if r["good"] and r["delta"] != 0 else ("down" if r["delta"] != 0 else "flat")
            delta_txt = f"{abs(r['delta']):.0%}p" if "rate" in r["key"] or "retention" in r["key"] else f"{abs(r['delta']):.0f}"
            hrows.append(
                f'<div class="hrow"><div class="hlabel">{t(lang, "history." + r["key"])}</div>'
                f'<div class="hval">{fmt(r["before"])} → <b>{fmt(r["after"])}</b> '
                f'<span class="hdelta {klass}">{arrow} {delta_txt}</span></div></div>'
            )
        history_card = (
            f'<div class="card"><h2>{t(lang, "history.title", date=history["date"])}</h2>'
            f'{"".join(hrows)}</div>'
        )

    funnel_card = ""
    if funnel and funnel["steps"][0]["count"] > 0:
        total = funnel["steps"][0]["count"]
        bars = []
        prev = total
        for step in funnel["steps"]:
            pct = step["count"] / total
            drop = f'<span class="drop">-{prev - step["count"]}</span>' if step["count"] < prev else ""
            bars.append(
                f'<div class="frow"><div class="flabel">{t(lang, "funnel." + step["key"])}</div>'
                f'<div class="fbar"><div class="ffill" style="width:{max(pct*100,2):.0f}%"></div></div>'
                f'<div class="fnum">{step["count"]} <small>({pct:.0%})</small> {drop}</div></div>'
            )
            prev = step["count"]
        median = ""
        if funnel["median_days_to_value"] is not None:
            median = f'<p class="note">{t(lang, "funnel.median_days", days=funnel["median_days_to_value"])}</p>'
        funnel_card = (
            f'<div class="card"><h2>{t(lang, "funnel.title")}</h2>{"".join(bars)}{median}</div>'
        )

    retention_card = ""
    if retention and len(retention) >= 3:
        W, H, PAD = 640, 170, 34
        n = len(retention)
        pts = []
        for i, r in enumerate(retention):
            x = PAD + i * (W - 2 * PAD) / max(n - 1, 1)
            y = H - PAD - r["rate"] * (H - 2 * PAD)
            pts.append((x, y, r))
        polyline = " ".join(f"{x:.0f},{y:.0f}" for x, y, _ in pts)
        dots = "".join(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="#2f7de1"/>'
            f'<text x="{x:.0f}" y="{y-12:.0f}" text-anchor="middle" font-size="15" fill="#222">{r["rate"]:.0%}</text>'
            f'<text x="{x:.0f}" y="{H-10}" text-anchor="middle" font-size="14" fill="#999">{t(lang, "retention.week", n=r["week"])}</text>'
            for x, y, r in pts
        )
        retention_card = (
            f'<div class="card"><h2>{t(lang, "retention.title")}</h2>'
            f'<p class="note" style="margin:0 0 6px">{t(lang, "retention.subtitle")}</p>'
            f'<svg viewBox="0 0 {W} {H}" style="width:100%;max-width:{W}px">'
            f'<line x1="{PAD}" y1="{H-PAD}" x2="{W-PAD}" y2="{H-PAD}" stroke="#ccc" stroke-width="1.5"/>'
            f'<polyline points="{polyline}" fill="none" stroke="#2f7de1" stroke-width="3.5" stroke-linejoin="round" stroke-linecap="round"/>'
            f"{dots}</svg></div>"
        )

    # 결론 카드는 리포트 맨 위에 온다 — 숫자를 읽기 전에 "그래서 뭘 하면 될까"부터.
    # 3초 안에 읽혀야 한다는 게 이 리포트의 유일한 요구사항이라서.
    insight_card = ""
    if insights:
        items = "".join(f"<li>{txt}</li>" for txt in insights)
        insight_card = (
            f'<div class="card ins lead"><h2>{t(lang, "report.insights_title")}</h2>'
            f"<ul>{items}</ul>"
            f'<p class="note">{t(lang, "report.insights_note")}</p></div>'
        )

    font_url, font_family = FONTS.get(lang, FONTS["en"])

    return f"""<!doctype html><html lang="{esc(lang)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dot Plot Report</title>
<link href="https://fonts.googleapis.com/css2?family={font_url}&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#fdfdfb;background-image:radial-gradient(#e8e6df 1px,transparent 1px);
  background-size:22px 22px;font-family:{font_family},sans-serif;color:#222;padding:40px 20px}}
.wrap{{max-width:940px;margin:0 auto}}
h1{{font-size:34px;margin:0 0 4px;font-weight:700}}
.sub{{font-size:18px;color:#777;margin:0 0 24px}}
.scroll{{overflow-x:auto}}
table{{border-collapse:collapse;background:transparent}}
th,td{{border:1.5px solid #222;width:52px;height:52px;text-align:center;font-size:19px}}
th{{border-top:none;font-weight:400;height:40px}}
th:first-child,td.name{{border:none;border-right:1.5px solid #222;text-align:left;
  padding-right:14px;width:110px;font-size:20px;white-space:nowrap}}
td.we,th.we{{background:#fae8dd}}
.dot,.orange,.ring{{display:inline-block;width:17px;height:17px;border-radius:50%;vertical-align:middle}}
.dot{{background:#2f7de1}}
.orange{{background:#e05c26}}
.ring{{background:transparent;border:4px solid #2f7de1;width:13px;height:13px}}
.aha{{display:inline-block;width:24px;height:24px;border-radius:6px;background:#e05c26;color:#fff;
  font-weight:700;font-size:16px;line-height:24px;vertical-align:middle}}
.legend{{display:flex;gap:26px;flex-wrap:wrap;margin:20px 0 34px;font-size:19px;align-items:center}}
.legend span{{display:flex;align-items:center;gap:8px}}
.aha.lg{{width:22px;height:22px;line-height:22px}}
.card{{border:2px solid #222;border-radius:14px;background:#fff;padding:18px 26px;margin-top:10px;
  box-shadow:4px 4px 0 #22222215}}
.card h2{{font-size:24px;margin:0 0 8px}}
.card ul{{margin:0;padding-left:22px;font-size:20px;line-height:1.9}}
.card.ins{{background:#fffbea;border-color:#e0a52a}}
.card.ins li{{margin-bottom:10px}}
.card.lead{{margin:0 0 26px}}
.card .note{{font-size:16px;color:#999;margin:12px 0 0}}
.chip{{display:flex;align-items:center;gap:8px;border:none;background:none;font:inherit;
  font-size:19px;cursor:pointer;padding:4px 8px;border-radius:8px}}
.chip:hover{{background:#2222220d}}
.chip.off{{opacity:.35}}
.chip.off .aha.lg::before{{content:"+ "}}
.hrow{{display:flex;align-items:center;gap:12px;margin:7px 0;font-size:20px}}
.hlabel{{width:220px;flex-shrink:0}}
.hdelta{{font-size:17px;margin-left:6px}}
.hdelta.up{{color:#0f8a3d}}
.hdelta.down{{color:#d0442c}}
.hdelta.flat{{color:#999}}
.ahacard{{border-width:2.5px}}
.agrid{{overflow-x:auto}}
.arow{{display:flex;align-items:center}}
.aname{{width:92px;flex-shrink:0;font-size:15px;color:#666;white-space:nowrap}}
.acell{{width:24px;height:24px;display:flex;align-items:center;justify-content:center;flex-shrink:0}}
.acell.ahead{{font-size:13px;color:#999;height:20px;white-space:nowrap}}
.acell.azero{{background:#2222220a;border-radius:4px}}
.adot{{width:12px;height:12px;border-radius:50%;background:#2f7de1}}
.aempty{{color:#ddd;font-size:12px}}
.aha.sm{{width:18px;height:18px;line-height:18px;font-size:12px;border-radius:4px}}
.frow{{display:flex;align-items:center;gap:12px;margin:8px 0}}
.flabel{{width:170px;font-size:19px;flex-shrink:0}}
.fbar{{flex:1;height:26px;background:#f1efe8;border-radius:6px;overflow:hidden}}
.ffill{{height:100%;background:#2f7de1;border-radius:6px}}
.fnum{{width:150px;font-size:18px;flex-shrink:0}}
.fnum small{{color:#999}}
.drop{{color:#d0442c;font-size:15px;margin-left:4px}}
</style></head><body><div class="wrap">
<h1>{t(lang, "report.title")}</h1>
<p class="sub">{t(lang, "report.subtitle", start=start.strftime('%Y.%m.%d'))}</p>
{insight_card}
<div class="scroll"><table>{head}{"".join(body)}</table></div>
<div class="legend">
  <span><span class="dot"></span> {t(lang, "report.legend.active")}</span>
  <span><span class="ring"></span> {t(lang, "report.legend.first")}</span>
  <span><span class="orange"></span> {t(lang, "report.legend.weekend_user")}</span>
  {aha_legend}
</div>
{aha_html}
<div class="card"><h2>{t(lang, "report.glance")}</h2><ul>{summary}</ul></div>
{funnel_card}
{retention_card}
{history_card}
<script>
const MARKS = {marks_js};
function repaint() {{
  document.querySelectorAll("td[data-ev]").forEach(td => {{
    const hit = td.dataset.ev.split("|").find(e => MARKS[e] && MARKS[e].on);
    if (hit) {{
      const m = MARKS[hit];
      td.innerHTML = '<span class="aha" style="background:' + m.c + '">' + m.l + '</span>';
    }} else {{
      td.innerHTML = td.dataset.base ? '<span class="' + td.dataset.base + '"></span>' : '';
    }}
  }});
}}
document.querySelectorAll(".chip").forEach(b => b.addEventListener("click", () => {{
  const ev = b.dataset.toggle;
  MARKS[ev].on = !MARKS[ev].on;
  b.classList.toggle("off", !MARKS[ev].on);
  repaint();
}}));
</script></div></body></html>"""
