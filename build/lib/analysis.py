"""핵심 계산 로직 — MCP와 무관한 순수 파이썬.

여기가 '1층(그리기)'과 '2층(패턴 찾기)'이다.
LLM은 이 코드를 건드리지 못하고, 결과만 받아서 해석한다.
그래서 숫자가 절대 안 틀린다.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

# '단골(regular)'의 유일한 정의 — 최근 2주 중 며칠 이상 핵심 가치 이벤트가 있어야 하는가.
# classify_users와 find_aha_moments가 반드시 같은 기준을 쓴다 (리포트 안에서 숫자가 어긋나지 않게).
REGULAR_DAYS_IN_2W = 10

# 허영 지표 — 가치를 증명하지 않는 이벤트. value_event로 못 쓰게 막고,
# 아하 후보에서도 뺀다. 이름만 다른 같은 개념들을 모아둔다.
VANITY_EVENTS = {
    "open_app", "app_open", "appopen", "open", "launch", "app_launch",
    "session_start", "session", "start_session", "visit", "view",
    "page_view", "pageview", "screen_view", "screenview", "impression",
}


def is_vanity(event: str) -> bool:
    return event.strip().lower() in VANITY_EVENTS


@dataclass
class UserRow:
    user_id: str
    platform: str
    signup: date                       # 처음 이벤트가 찍힌 날
    value_days: set[date] = field(default_factory=set)   # 핵심 가치 이벤트를 한 날들
    special_days: dict[date, set[str]] = field(default_factory=dict)  # 그날 한 특별 이벤트들


def load_events(csv_path: str) -> list[dict]:
    with open(csv_path, newline="") as f:
        return [
            {**row, "date": date.fromisoformat(row["date"])}
            for row in csv.DictReader(f)
        ]


class ValueEventError(ValueError):
    """value_event가 데이터에 없거나 허영 지표일 때. 조용히 0%를 내지 않고 즉시 알린다."""


def check_value_event(events: list[dict], value_event: str) -> None:
    """분석 전에 value_event를 검증한다.

    오타 하나로 '이탈률 100%, 리텐션 0%' 리포트가 나가는 걸 막는 게 목적이다.
    (데이터에 없는 이벤트는 아무도 가치를 못 얻은 것처럼 계산되기 때문)
    """
    if is_vanity(value_event):
        raise ValueEventError(
            f"'{value_event}'는 허영 지표라 핵심 가치 이벤트로 쓸 수 없습니다. "
            "앱을 열었다는 건 가치를 얻었다는 뜻이 아닙니다. "
            "'그 행동을 했으면 이 서비스를 쓴 보람이 있다'고 할 만한 이벤트를 고르세요 "
            "(예: play_song, purchase, send_message)."
        )
    present = {e["event"] for e in events}
    if value_event not in present:
        options = sorted(e for e in present if not is_vanity(e))
        raise ValueEventError(
            f"'{value_event}'는 데이터에 없는 이벤트입니다. "
            f"고를 수 있는 이벤트: {options or sorted(present)}"
        )


def build_users(events: list[dict], value_event: str) -> dict[str, UserRow]:
    """이벤트 로그를 '유저 한 명 = 한 줄' 구조로 바꾼다. 도트 플롯의 뼈대."""
    users: dict[str, UserRow] = {}
    for e in events:
        u = users.get(e["user_id"])
        if u is None:
            # platform은 선택 컬럼 — 3컬럼 CSV(user_id, date, event)도 그대로 동작한다
            u = users[e["user_id"]] = UserRow(
                e["user_id"], e.get("platform") or "unknown", e["date"]
            )
        u.signup = min(u.signup, e["date"])
        if e["event"] == value_event:
            u.value_days.add(e["date"])
        elif not is_vanity(e["event"]):  # 허영 지표는 특별 표시에서 제외
            u.special_days.setdefault(e["date"], set()).add(e["event"])
    return users


def render_dot_plot(
    users: dict[str, UserRow],
    start: date,
    days: int,
    marks: dict[str, str] | None = None,   # {"search": "S", "create_playlist": "P"}
    lang: str = "en",
) -> str:
    """인스타 그림과 같은 표를 텍스트로 그린다.
    ◎ = 가입일에 활동, ● = 활동, S/P = 특별 이벤트, · = 없음
    """
    from i18n import t

    marks = marks or {}
    dates = [start + timedelta(days=i) for i in range(days)]
    weekdays = t(lang, "weekdays").split(",")
    header = "user        │ " + " ".join(weekdays[d.weekday()] for d in dates)
    lines = [header, "─" * len(header)]
    for u in sorted(users.values(), key=lambda x: x.signup):
        cells = []
        for d in dates:
            special = u.special_days.get(d, set())
            mark = next((marks[m] for m in marks if m in special), None)
            if d in u.value_days:
                cell = "◎" if d == u.signup else "●"
                if mark:
                    cell = mark  # 특별 이벤트가 있으면 그 글자로 표시
            else:
                cell = mark or "·"
            cells.append(cell)
        label = f"{u.user_id} {u.platform[:3]}"
        lines.append(f"{label:<11} │ " + " ".join(cells))
    return "\n".join(lines)


def classify_users(users: dict[str, UserRow], today: date) -> dict[str, list[str]]:
    """2층: 눈으로 찾던 패턴을 규칙으로 찾는다.
    반환 키는 언어 중립 코드 — 화면에 보여줄 땐 i18n.t(lang, f"bucket.{key}")로 번역."""
    buckets: dict[str, list[str]] = defaultdict(list)
    for u in users.values():
        active = sorted(u.value_days)
        tenure = (today - u.signup).days + 1
        recent2w = [d for d in active if (today - d).days < 14]
        if len(active) <= 1 and tenure >= 7:
            buckets["churned"].append(u.user_id)
        elif active and all(d.weekday() >= 5 for d in active) and len(active) >= 2:
            buckets["weekend_only"].append(u.user_id)
        elif tenure >= 14 and len(recent2w) >= REGULAR_DAYS_IN_2W:
            buckets["regular"].append(u.user_id)
        else:
            buckets["casual"].append(u.user_id)
    return dict(buckets)


def find_aha_moments(
    events: list[dict],
    users: dict[str, UserRow],
    value_event: str,
    today: date,
    min_group: int = 5,
) -> list[dict]:
    """3층의 재료: 모든 후보 이벤트를 자동으로 훑어서
    '이 행동을 한 유저가 나중에 단골이 되는가'를 계산한다.

    단골 정의는 classify_users와 동일하다 (REGULAR_DAYS_IN_2W) — 같은 리포트 안에서
    '단골'이라는 말이 두 가지 뜻을 갖지 않게.
    """
    def is_regular(u: UserRow) -> bool:
        return sum(1 for d in u.value_days if (today - d).days < 14) >= REGULAR_DAYS_IN_2W

    candidates = {e["event"] for e in events} - {value_event}
    candidates = {ev for ev in candidates if not is_vanity(ev)}
    did_event: dict[str, set[str]] = defaultdict(set)
    first_did: dict[str, dict[str, date]] = defaultdict(dict)  # event -> user -> 처음 한 날
    for e in events:
        if e["event"] in candidates:
            did_event[e["event"]].add(e["user_id"])
            prev = first_did[e["event"]].get(e["user_id"])
            if prev is None or e["date"] < prev:
                first_did[e["event"]][e["user_id"]] = e["date"]

    results = []
    for ev, doers in did_event.items():
        group_a = [u for u in users.values() if u.user_id in doers]
        group_b = [u for u in users.values() if u.user_id not in doers]
        if len(group_a) < min_group or len(group_b) < min_group:
            continue  # 표본이 너무 작으면 판단 보류 — 함부로 단정하지 않는다
        rate_a = sum(map(is_regular, group_a)) / len(group_a)
        rate_b = sum(map(is_regular, group_b)) / len(group_b)

        # 핵심 지표: 같은 유저의 그 행동 '전 vs 후' 활동률 변화.
        # 자주 오는 유저는 아무 이벤트나 다 하므로 집단 비교(lift)는 잡음에 속지만,
        # 전/후 비교는 "이 행동을 기점으로 습관이 바뀌었나"만 본다 (YC 원래 통찰).
        changes = []
        for u in group_a:
            first = first_did[ev][u.user_id]
            pre_days = (first - u.signup).days
            post_days = (today - first).days
            if pre_days < 3 or post_days < 3:
                continue  # 전/후 구간이 너무 짧으면 판단 불가
            pre_rate = sum(1 for d in u.value_days if u.signup <= d < first) / pre_days
            post_rate = sum(1 for d in u.value_days if d >= first) / (post_days + 1)
            changes.append(post_rate - pre_rate)
        behavior_change = (
            round(sum(changes) / len(changes), 2) if len(changes) >= min_group else None
        )

        results.append({
            "event": ev,
            "did_count": len(group_a),
            "did_regular_rate": round(rate_a, 2),
            "not_count": len(group_b),
            "not_regular_rate": round(rate_b, 2),
            "lift": round(rate_a - rate_b, 2),
            "behavior_change": behavior_change,       # 전/후 활동률 변화 (신뢰도 높음)
            "change_sample": len(changes),
        })
    # 전/후 변화가 측정된 이벤트 우선, 그 안에서 변화량 큰 순 — 잡음 이벤트는 자연히 뒤로
    return sorted(
        results,
        key=lambda r: (r["behavior_change"] is None, -(r["behavior_change"] or -1), -r["lift"]),
    )


def audit_tracking(code_events: list[str], data_events: set[str]) -> dict:
    """코드에서 찾은 이벤트 목록과 실제 데이터에 찍힌 이벤트를 대조한다.

    - 코드에만 있음 → 심어놨는데 한 번도 안 찍힘 (고장이거나, 아무도 안 쓰는 기능)
    - 데이터에만 있음 → 코드에서 못 찾음 (죽은 코드거나, 스캔 누락)
    - 양쪽 다 있음 → 정상 추적 중
    """
    code = set(code_events)
    return {
        "tracked_ok": sorted(code & data_events),
        "in_code_never_fired": sorted(code - data_events),
        "in_data_not_in_code": sorted(data_events - code),
    }


def onboarding_funnel(users: dict[str, UserRow], today: date) -> dict:
    """온보딩 퍼널: 새 유저가 어느 계단에서 떨어지는지.

    계단 정의 (어떤 서비스든 통하는 일반형):
      가입 → 첫 가치 이벤트 → 다른 날 재방문 → 최근 2주 내 활동
    함께 계산: 가입~첫 가치까지 걸린 날의 중앙값 (온보딩 마찰 지표)
    """
    total = len(users)
    got_value = [u for u in users.values() if u.value_days]
    returned = [u for u in got_value if len(u.value_days) >= 2]
    recent = [u for u in returned if any((today - d).days < 14 for d in u.value_days)]

    lags = sorted((min(u.value_days) - u.signup).days for u in got_value)
    median_lag = lags[len(lags) // 2] if lags else None

    return {
        "steps": [
            {"key": "signup", "count": total},
            {"key": "first_value", "count": len(got_value)},
            {"key": "returned", "count": len(returned)},
            {"key": "recent", "count": len(recent)},
        ],
        "median_days_to_value": median_lag,
    }


def retention_curve(users: dict[str, UserRow], today: date, max_weeks: int = 6) -> list[dict]:
    """주차별 리텐션: 가입 후 N주차에 가치 이벤트가 있는 유저 비율.

    N주차를 관측할 수 있을 만큼 오래된 유저만 분모에 넣는다 (미래를 세지 않기).
    """
    out = []
    for week in range(max_weeks + 1):
        eligible = [
            u for u in users.values()
            if (today - u.signup).days >= (week + 1) * 7 - 1
        ]
        if len(eligible) < 5:
            break  # 표본 5명 미만 주차는 신뢰 불가 — 자르기
        active = sum(
            1 for u in eligible
            if any(week * 7 <= (d - u.signup).days < (week + 1) * 7 for d in u.value_days)
        )
        out.append({"week": week, "eligible": len(eligible), "rate": round(active / len(eligible), 3)})
    return out
