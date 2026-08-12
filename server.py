# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.2.0"]
# ///
"""Dot Plot MCP 서버 — 얇은 껍데기.

계산은 전부 analysis.py가 하고, 여기서는 그걸 MCP 툴로 노출만 한다.
Claude가 이 툴들을 부르면:
  1층 dot_plot        → 표를 그려준다 (계산: 코드)
  2층 classify_users  → 패턴을 찾아준다 (계산: 코드)
  3층 find_aha_moments→ 아하 모먼트 후보를 준다 (계산: 코드)
그다음 '그래서 뭘 해야 하는지' 해석은 Claude가 한다. ← 여기가 상품
"""
from datetime import date, timedelta

from mcp.server import MCPServer

import analysis

mcp = MCPServer("dotplot")


@mcp.tool()
def describe_events(csv_path: str) -> dict:
    """이벤트 CSV의 구조를 파악한다: 기간, 유저 수, 이벤트 종류별 개수.
    분석 시작 전에 항상 먼저 불러서 어떤 이벤트가 있는지 확인할 것."""
    events = analysis.load_events(csv_path)
    counts: dict[str, int] = {}
    for e in events:
        counts[e["event"]] = counts.get(e["event"], 0) + 1
    dates = [e["date"] for e in events]
    return {
        "users": len({e["user_id"] for e in events}),
        "events_total": len(events),
        "event_types": dict(sorted(counts.items(), key=lambda x: -x[1])),
        "date_range": [min(dates).isoformat(), max(dates).isoformat()],
        "hint": "value_event로는 '진짜 가치를 얻은 행동'을 골라라. open_app 같은 허영 지표 금지.",
    }


@mcp.tool()
def dot_plot(
    csv_path: str,
    value_event: str,
    mark_events: dict[str, str] | None = None,
    weeks: int = 6,
    lang: str = "en",
) -> str:
    """유저 한 명 = 한 줄, 하루 = 한 칸인 도트 플롯을 그린다.
    ◎=첫 활동일, ●=핵심 가치 이벤트 발생, ·=없음.
    mark_events로 특별 이벤트에 글자를 붙일 수 있다. 예: {"create_playlist": "P"}"""
    events = analysis.load_events(csv_path)
    users = analysis.build_users(events, value_event)
    start = min(e["date"] for e in events)
    return analysis.render_dot_plot(users, start, weeks * 7, mark_events, lang=lang)


@mcp.tool()
def classify_users(csv_path: str, value_event: str, lang: str = "en") -> dict:
    """유저를 행동 패턴별로 자동 분류한다:
    churned(한번 쓰고 떠남) / weekend_only(주말만) / regular(찐팬) / casual(가끔).
    lang: 사람이 읽을 라벨의 언어 (en/ko/ja)."""
    from i18n import t

    events = analysis.load_events(csv_path)
    users = analysis.build_users(events, value_event)
    today = max(e["date"] for e in events)
    buckets = analysis.classify_users(users, today)
    return {
        k: {"label": t(lang, f"bucket.{k}"), "count": len(v), "users": v}
        for k, v in buckets.items()
    }


@mcp.tool()
def find_aha_moments(csv_path: str, value_event: str) -> dict:
    """모든 후보 이벤트를 자동으로 훑어서 아하 모먼트 후보를 찾는다.
    '이 행동을 한 유저는 단골이 될 확률이 얼마나 높아지는가(lift)'를 계산.
    주의: 상관관계일 뿐 인과가 아니다 — 반드시 실험으로 확인하라고 안내할 것."""
    events = analysis.load_events(csv_path)
    users = analysis.build_users(events, value_event)
    today = max(e["date"] for e in events)
    return {
        "candidates": analysis.find_aha_moments(events, users, value_event, today),
        "caution": "lift가 크더라도 상관관계다. 온보딩에 넣어 A/B 테스트로 검증하라.",
    }


@mcp.tool()
def audit_tracking(code_events: list[str], csv_path: str) -> dict:
    """코드에 심어진 이벤트와 실제 데이터에 찍힌 이벤트를 대조한다.

    사용법 (에이전트 지침):
    1. 먼저 프로젝트 코드에서 이벤트 로깅 호출을 직접 찾아라.
       흔한 패턴: logEvent(...), track(...), analytics.capture(...),
       posthog.capture(...), gtag('event', ...), mixpanel.track(...)
    2. 찾아낸 이벤트 이름 목록을 code_events로 넘겨라.
    3. 결과 해석:
       - '코드에만 있음' → 로깅이 고장났거나 그 기능을 아무도 안 쓴다
       - '데이터에만 있음' → 죽은 코드이거나 네 스캔이 누락했다 (다시 찾아볼 것)
    4. 추가로, 코드에서 본 '중요한 기능인데 로깅이 아예 없는 곳'
       (버튼 핸들러, 핵심 액션)을 사용자에게 보고하고 심어줄지 물어라."""
    events = analysis.load_events(csv_path)
    data_events = {e["event"] for e in events}
    return analysis.audit_tracking(code_events, data_events)


@mcp.tool()
def get_report_strings() -> dict:
    """리포트에 들어가는 번역 가능한 문장 전체(영어 원본)를 반환한다.

    내장 언어(en/ko/ja)가 아닌 언어로 리포트를 만들 때:
    1. 이 툴을 불러 영어 원본을 받는다
    2. 값들을 사용자의 언어로 번역한다 — {n}, {rate_did} 같은
       중괄호 자리표시자는 반드시 그대로 남길 것 (숫자가 들어갈 자리)
    3. generate_report에 custom_strings로 넘기고 lang="custom"으로 호출한다"""
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
    """YC 손그림 스타일의 HTML 도트 플롯 리포트를 생성한다.
    비개발자도 3초 안에 읽을 수 있는 형태 — 투자자/팀 공유용.
    mark_events로 특별 이벤트들을 글자로 표시한다 (여러 개 가능, 색 자동 배정).
    예: mark_events={"create_playlist": "P", "share": "S"},
        mark_labels={"create_playlist": "P = created a playlist", "share": "S = shared"}
    find_aha_moments의 상위 후보들을 마크로 넣으면 리포트가 제일 유용해진다.

    언어: 사용자의 대화 언어에 맞춰라.
    - 내장 언어면 lang="en"|"ko"|"ja"
    - 그 외 언어(프랑스어, 스페인어, 힌디어...)는 get_report_strings()를 받아
      번역한 뒤 custom_strings로 넘기고 lang="custom"으로 호출.
      {중괄호} 자리표시자는 절대 번역하지 말 것."""
    import report as report_mod

    if custom_strings:
        from i18n import register_custom

        bad = register_custom(custom_strings)
        lang = "custom"
        if bad:
            return f"번역 오류 — 다음 키를 고쳐서 다시 호출하세요: {bad}"

    events = analysis.load_events(csv_path)
    users = analysis.build_users(events, value_event)
    start = min(e["date"] for e in events)
    today = max(e["date"] for e in events)
    subset = dict(sorted(users.items(), key=lambda kv: kv[1].signup)[:max_users])
    # 인사이트는 표에 보이는 일부가 아니라 전체 유저 기준으로 계산한다
    buckets = analysis.classify_users(users, today)
    aha_results = analysis.find_aha_moments(events, users, value_event, today)
    labels = {ev: lbl.split("=")[-1].strip() for ev, lbl in (mark_labels or {}).items()}
    insights = report_mod.build_insights(len(users), buckets, aha_results, labels, lang=lang)
    html = report_mod.render_html_report(
        subset, start, weeks * 7, today,
        mark_events=mark_events, mark_labels=mark_labels,
        insights=insights, lang=lang,
    )
    with open(output_path, "w") as f:
        f.write(html)
    return f"리포트 생성 완료: {output_path} (유저 {len(subset)}명, {weeks}주)"


HOSTING_DIR = "hosting"  # server.py 옆의 Vercel 프로젝트 폴더


@mcp.tool()
def publish_report(html_path: str) -> dict:
    """생성된 HTML 리포트를 호스팅하고 공유 링크를 발급한다.

    구현: hosting/ 폴더(Vercel 프로젝트)에 무작위 주소로 리포트를 넣고
    `vercel deploy --prod`로 배포한다. 링크를 아는 사람만 접근 가능하고
    (무작위 주소 + noindex 헤더), 검색엔진에도 안 잡힌다.
    필요 조건: vercel CLI 로그인. 삭제: hosting/r/에서 파일 지우고 재배포.
    주의: 웹에 올라가는 것이므로, 올리기 전 사용자에게 확인할 것."""
    import re
    import secrets
    import shutil
    import subprocess
    from pathlib import Path

    path = Path(html_path).resolve()
    if not path.exists():
        return {"error": f"파일이 없음: {path}"}

    hosting = Path(__file__).parent / HOSTING_DIR
    (hosting / "r").mkdir(parents=True, exist_ok=True)

    report_id = secrets.token_hex(6)
    dest = f"r/{report_id}.html"
    shutil.copy(path, hosting / dest)

    r = subprocess.run(
        ["vercel", "deploy", "--prod", "--yes"],
        capture_output=True, text=True, cwd=hosting,
    )
    if r.returncode != 0:
        return {"error": f"배포 실패: {r.stderr.strip()[-500:]}"}

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
            return {"error": f"배포는 됐지만 URL 해석 실패: {r.stdout[-300:]}"}
    return {
        "공유 링크 (이걸 보내면 됨)": f"{base}/{dest}",
        "삭제 방법": f"{HOSTING_DIR}/{dest} 파일 삭제 후 재배포",
        "참고": "무작위 주소 + noindex — 링크를 아는 사람만 접근 가능",
    }


@mcp.tool()
def submit_benchmark(
    csv_path: str, value_event: str, industry: str, stage: str, consent: bool = False
) -> dict:
    """익명 벤치마크에 집계값을 제출한다 (옵트인).

    반드시 지킬 것: consent=True는 사용자가 명시적으로 동의했을 때만.
    동의를 구할 때 '서버로 가는 것'을 그대로 보여줘라 — 집계값 5개
    (유저 수, 이탈률, 주말비율, 단골률, 아하 lift)가 전부이고,
    유저 ID·이벤트 로그·서비스 이름은 절대 전송되지 않는다.
    industry: b2c|b2b|commerce|content|social|tool|game|other
    stage: pre_launch|under_100_users|under_1k_users|over_1k_users"""
    import benchmark as bench

    if not consent:
        return {"error": "사용자 동의가 필요합니다. 전송 내용을 보여주고 허락받은 뒤 consent=True로 다시 호출하세요."}
    if industry not in bench.INDUSTRIES or stage not in bench.STAGES:
        return {"error": f"industry는 {bench.INDUSTRIES}, stage는 {bench.STAGES} 중 하나"}

    events = analysis.load_events(csv_path)
    users = analysis.build_users(events, value_event)
    today = max(e["date"] for e in events)
    agg = bench.compute_aggregates(events, users, value_event, today)
    bench.submit(agg, industry, stage)
    return {"제출 완료": agg, "참고": "이 집계값 외에는 아무것도 전송되지 않았습니다."}


@mcp.tool()
def compare_benchmark(csv_path: str, value_event: str, industry: str, stage: str) -> dict:
    """내 지표를 같은 업종·단계 팀들의 백분위와 비교한다.
    표본이 10팀 미만이면 비교가 무의미하므로 그렇게 안내할 것."""
    import benchmark as bench

    events = analysis.load_events(csv_path)
    users = analysis.build_users(events, value_event)
    today = max(e["date"] for e in events)
    mine = bench.compute_aggregates(events, users, value_event, today)
    peers = bench.fetch(industry, stage)

    result = {"내 지표": mine, "같은 그룹 통계": peers}
    if not peers or (peers.get("sample_size") or 0) < 10:
        result["주의"] = f"표본이 {peers.get('sample_size', 0)}팀뿐 — 아직 비교 기준으로 삼지 마세요."
    return result


if __name__ == "__main__":
    mcp.run()
