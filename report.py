"""HTML 리포트 생성 — YC 손그림 도트 플롯 스타일.

디자인 원칙 (참고 이미지 그대로):
  - 공책 종이 느낌: 흰 바탕 + 옅은 점 패턴, 손글씨 폰트
  - 검은 얇은 격자, 주말 세로줄은 살구색으로 통째로 칠함
  - 파란 점 = 활동, ◎ 고리 = 가입일, 주황 점 = 주말에만 쓰는 유저
  - 제일 중요한 것: 설명 없이도 3초 안에 읽혀야 한다
"""
from __future__ import annotations

from datetime import date, timedelta

from analysis import UserRow, classify_users

WEEKDAY = ["M", "T", "W", "TH", "F", "SA", "S"]


def build_insights(
    all_users_count: int,
    buckets: dict[str, list[str]],
    aha_results: list[dict],
    event_labels: dict[str, str] | None = None,
) -> list[str]:
    """계산된 숫자를 쉬운 문장으로 바꾼다 — 전부 규칙 기반, LLM 없음.
    과장 금지: 항상 숫자를 병기하고, 행동 제안은 '해보세요/확인해보세요'로 끝낸다."""
    labels = event_labels or {}
    out = []

    # ① 아하 모먼트 — 차이가 충분히 클 때만 말한다
    if aha_results and aha_results[0]["lift"] >= 0.3:
        top = aha_results[0]
        name = labels.get(top["event"], top["event"])
        out.append(
            f"💡 <b>'{name}'</b>을(를) 한 유저 {top['did_count']}명 중 "
            f"<b>{top['did_regular_rate']:.0%}</b>가 단골이 됐어요. "
            f"안 한 유저는 {top['not_regular_rate']:.0%}뿐이에요. "
            f"→ 가입 직후에 이걸 하게 유도하고, 효과가 진짜인지 확인해보세요."
        )

    # ② 이탈 경고 — 전체의 1/4 이상이 한 번 쓰고 떠났을 때
    for name, ids in buckets.items():
        if "떠남" in name and len(ids) / all_users_count >= 0.25:
            out.append(
                f"⚠️ 전체 {all_users_count}명 중 <b>{len(ids)}명({len(ids)/all_users_count:.0%})</b>이 "
                f"한 번 쓰고 돌아오지 않았어요. → 첫날 경험(온보딩)을 점검해보세요."
            )

    # ③ 주말 유저 — 존재하면 알려준다
    for name, ids in buckets.items():
        if "주말" in name and len(ids) >= 3:
            out.append(
                f"📅 <b>{len(ids)}명</b>은 주말에만 써요. "
                f"→ 주중 사용을 막는 게 뭔지, 그 유저 한 명에게 직접 물어보세요."
            )

    if not out:
        out.append("아직 뚜렷한 패턴이 없어요. 데이터가 더 쌓이면 다시 확인해보세요.")
    return out


def render_html_report(
    users: dict[str, UserRow],
    start: date,
    days: int,
    today: date,
    aha_event_label: str | None = None,   # 예: "P = 플레이리스트 만든 날"
    aha_event: str | None = None,          # 예: "create_playlist"
    insights: list[str] | None = None,
) -> str:
    buckets = classify_users(users, today)
    weekend_only = set()
    for name, ids in buckets.items():
        if "주말" in name:
            weekend_only.update(ids)

    dates = [start + timedelta(days=i) for i in range(days)]

    # 헤더 행
    head = "<tr><th></th>" + "".join(
        f'<th class="{"we" if d.weekday() >= 5 else ""}">{WEEKDAY[d.weekday()]}</th>'
        for d in dates
    ) + "</tr>"

    # 유저 행 — 가입 빠른 순
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

    # 한눈에 보기 — 쉬운 말 3줄
    summary = "".join(
        f"<li><b>{len(ids)}명</b> — {name}</li>"
        for name, ids in sorted(buckets.items(), key=lambda x: -len(x[1]))
    )

    aha_legend = (
        f'<span><span class="aha lg">P</span> {aha_event_label}</span>' if aha_event_label else ""
    )

    insight_card = ""
    if insights:
        items = "".join(f"<li>{t}</li>" for t in insights)
        insight_card = (
            '<div class="card ins"><h2>그래서, 뭘 하면 될까?</h2>'
            f"<ul>{items}</ul>"
            '<p class="note">* 자동 계산된 참고용이에요. 인과관계는 실험으로 확인하세요.</p></div>'
        )

    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Dot Plot Report</title>
<link href="https://fonts.googleapis.com/css2?family=Patrick+Hand&family=Gaegu:wght@400;700&display=swap" rel="stylesheet">
<style>
body{{margin:0;background:#fdfdfb;background-image:radial-gradient(#e8e6df 1px,transparent 1px);
  background-size:22px 22px;font-family:'Gaegu','Patrick Hand',sans-serif;color:#222;padding:40px 20px}}
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
<h1>우리 유저들, 진짜로 쓰고 있나?</h1>
<p class="sub">한 줄 = 유저 한 명 · 한 칸 = 하루 ({start.strftime('%Y.%m.%d')} ~)</p>
<div class="scroll"><table>{head}{"".join(body)}</table></div>
<div class="legend">
  <span><span class="dot"></span> 쓴 날</span>
  <span><span class="ring"></span> 처음 쓴 날</span>
  <span><span class="orange"></span> 주말에만 쓰는 유저</span>
  {aha_legend}
</div>
<div class="card"><h2>한눈에 보기</h2><ul>{summary}</ul></div>
{insight_card}
</div></body></html>"""
