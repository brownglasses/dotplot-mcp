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

from analysis import UserRow, classify_users
from i18n import t

WEEKDAY_EN = ["M", "T", "W", "TH", "F", "SA", "S"]

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

    if aha_results and aha_results[0]["lift"] >= 0.3:
        top = aha_results[0]
        out.append(t(lang, "insight.aha",
            name=labels.get(top["event"], top["event"]),
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
    aha_event_label: str | None = None,   # 예: "P = created a playlist"
    aha_event: str | None = None,          # 예: "create_playlist"
    insights: list[str] | None = None,
    lang: str = "en",
) -> str:
    buckets = classify_users(users, today)
    weekend_only = set(buckets.get("weekend_only", []))

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
            inner = ""
            if aha_event and aha_event in u.special_days.get(d, set()):
                inner = '<span class="aha">P</span>'
            elif d in u.value_days:
                dot = "ring" if d == u.signup else ("orange" if u.user_id in weekend_only else "dot")
                inner = f'<span class="{dot}"></span>'
            cells.append(f'<td class="{klass}">{inner}</td>')
        body.append(f'<tr><td class="name">{u.user_id.upper()}</td>{"".join(cells)}</tr>')

    summary = "".join(
        f'<li>{t(lang, "report.glance_item", n=len(ids), label=t(lang, f"bucket.{key}"))}</li>'
        for key, ids in sorted(buckets.items(), key=lambda x: -len(x[1]))
    )

    aha_legend = (
        f'<span><span class="aha lg">P</span> {aha_event_label}</span>' if aha_event_label else ""
    )

    insight_card = ""
    if insights:
        items = "".join(f"<li>{txt}</li>" for txt in insights)
        insight_card = (
            f'<div class="card ins"><h2>{t(lang, "report.insights_title")}</h2>'
            f"<ul>{items}</ul>"
            f'<p class="note">{t(lang, "report.insights_note")}</p></div>'
        )

    font_url, font_family = FONTS.get(lang, FONTS["en"])

    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
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
.card .note{{font-size:16px;color:#999;margin:12px 0 0}}
</style></head><body><div class="wrap">
<h1>{t(lang, "report.title")}</h1>
<p class="sub">{t(lang, "report.subtitle", start=start.strftime('%Y.%m.%d'))}</p>
<div class="scroll"><table>{head}{"".join(body)}</table></div>
<div class="legend">
  <span><span class="dot"></span> {t(lang, "report.legend.active")}</span>
  <span><span class="ring"></span> {t(lang, "report.legend.first")}</span>
  <span><span class="orange"></span> {t(lang, "report.legend.weekend_user")}</span>
  {aha_legend}
</div>
<div class="card"><h2>{t(lang, "report.glance")}</h2><ul>{summary}</ul></div>
{insight_card}
</div></body></html>"""
