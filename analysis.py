"""핵심 계산 로직 — MCP와 무관한 순수 파이썬.

여기가 '1층(그리기)'과 '2층(패턴 찾기)'이다.
LLM은 이 코드를 건드리지 못하고, 결과만 받아서 해석한다.
그래서 숫자가 절대 안 틀린다.
"""
from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

# '단골(regular)'의 유일한 정의 — 최근 2주 중 며칠 이상 핵심 가치 이벤트가 있어야 하는가.
# classify_users와 find_aha_moments가 반드시 같은 기준을 쓴다 (리포트 안에서 숫자가 어긋나지 않게).
REGULAR_DAYS_IN_2W = 10

# 유저를 판정하려면 그만큼 지켜본 뒤여야 한다. 이 두 숫자가 곧
# "로깅을 심었으면 언제 다시 오면 되는가"의 답이기도 하다 (tracking_plan이 그대로 쓴다).
CHURN_JUDGEMENT_DAYS = 7    # 이만큼 지나야 '한 번 쓰고 떠났다'고 말할 수 있다
REGULAR_JUDGEMENT_DAYS = 14  # 이만큼 지나야 단골 판정과 1주차 리텐션이 나온다

# 허영 지표 — 가치를 증명하지 않는 이벤트. value_event로 못 쓰게 막고,
# 아하 후보에서도 뺀다. 이름만 다른 같은 개념들을 모아둔다.
VANITY_EVENTS = {
    "open_app", "app_open", "appopen", "open", "launch", "app_launch",
    "session_start", "session", "start_session", "visit", "view",
    "page_view", "pageview", "screen_view", "screenview", "impression",
}


def is_vanity(event: str) -> bool:
    return event.strip().lower() in VANITY_EVENTS


# 핵심 가치 이벤트가 되려면 최소한 이 정도는 돼야 한다는 선.
# 넘겼다고 좋은 선택인 건 아니고, 못 넘기면 확실히 나쁜 선택이라는 뜻이다.
MIN_COVERAGE = 0.2      # 유저 5명 중 1명도 안 하는 행동은 제품의 핵심일 수 없다
MIN_DAYS_PER_USER = 1.2  # 한 번 하고 마는 행동은 '돌아왔는가'를 말해주지 않는다


def rank_value_events(events: list[dict]) -> list[dict]:
    """value_event 후보를 순위 매긴다 — 코드가 할 수 있는 만큼만.

    코드가 판단할 수 있는 것: 얼마나 많은 유저가 하는가(coverage),
    반복되는 행동인가(days_per_user), 허영 지표인가.

    코드가 판단할 수 없는 것: 그 행동이 '가치'인가. `purchase`와 `view_item`은
    숫자로는 똑같이 생겼다. 그건 제품을 아는 쪽 — 코드를 읽은 에이전트가 판단해야
    한다. 그래서 여기서는 고르지 않고 근거만 붙여 줄을 세운다.
    """
    total_users = len({e["user_id"] for e in events})
    if not total_users:
        return []

    days: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for e in events:
        days[e["event"]][e["user_id"]].add(e["date"])

    ranked = []
    for ev, doers in days.items():
        if is_vanity(ev):
            continue
        coverage = len(doers) / total_users
        per_user = sum(len(d) for d in doers.values()) / len(doers)
        ranked.append({
            "event": ev,
            "users": len(doers),
            "coverage": round(coverage, 3),
            "days_per_user": round(per_user, 2),
            "usable": coverage >= MIN_COVERAGE and per_user >= MIN_DAYS_PER_USER,
        })
    ranked.sort(key=lambda r: (not r["usable"], -r["coverage"], -r["days_per_user"]))
    return ranked


@dataclass
class UserRow:
    user_id: str
    platform: str
    signup: date                       # 처음 이벤트가 찍힌 날
    value_days: set[date] = field(default_factory=set)   # 핵심 가치 이벤트를 한 날들
    special_days: dict[date, set[str]] = field(default_factory=dict)  # 그날 한 특별 이벤트들


# 컬럼 이름은 도구마다 다르다. 드라이버를 늘리는 대신 이름을 알아보는 쪽이
# 훨씬 넓게 커버된다 — psql, mysql, mongoexport, bq, 스프레드시트 전부 여기 걸린다.
COLUMN_ALIASES = {
    "user_id": ("user_id", "userid", "user", "uid", "customer_id", "account_id",
                "person_id", "distinct_id", "profile_id", "id"),
    "date": ("date", "day", "created_at", "createdat", "occurred_at", "inserted_at",
             "event_date", "timestamp", "time", "ts", "at"),
    "event": ("event", "event_name", "eventname", "event_type", "action", "type", "name"),
    "platform": ("platform", "device", "os", "client"),   # 선택
}


class EventFileError(ValueError):
    """파일을 이벤트로 읽을 수 없을 때. 무엇이 문제고 무엇을 주면 되는지 같이 말한다."""


def parse_day(value) -> date:
    """DB가 주는 온갖 시각 표현에서 '날짜'만 뽑는다.

    도트 플롯의 한 칸은 하루다. 시·분·초와 시간대는 필요 없다.
    애매한 형식(07/01/2026 — 7월 1일인지 1월 7일인지)은 추측하지 않고 거절한다.
    잘못 읽은 날짜는 조용히 틀린 리포트가 되기 때문이다.
    """
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        n = float(value)
        if n > 1e11:      # 밀리초 epoch
            n /= 1000
        return datetime.fromtimestamp(n, tz=timezone.utc).date()

    s = str(value).strip()
    if not s:
        raise EventFileError("A row has an empty date.")
    try:
        return date.fromisoformat(s[:10])          # ISO 날짜, ISO 타임스탬프 둘 다 여기서 끝난다
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y/%m/%d", "%Y.%m.%d", "%d %b %Y", "%b %d %Y", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise EventFileError(
        f"Can't read {s!r} as a date. Export dates as ISO — 2026-07-01, or a "
        "full timestamp like 2026-07-01T10:23:00Z. Formats like 07/01/2026 are "
        "ambiguous and are refused rather than guessed at."
    )


def _match_columns(fields: list[str]) -> dict[str, str]:
    """파일의 실제 컬럼명을 user_id / date / event 로 대응시킨다."""
    lowered = {f.lower().strip(): f for f in fields}
    found: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lowered:
                found[canonical] = lowered[alias]
                break
    missing = [c for c in ("user_id", "date", "event") if c not in found]
    if missing:
        raise EventFileError(
            f"Missing {missing} — the file has {fields}. Rename the columns, or "
            "alias them in your query: SELECT user_id, created_at AS date, "
            "'purchase' AS event FROM orders"
        )
    return found


def _read_rows(path: str) -> list[dict]:
    """CSV / TSV / JSON / JSONL 중 무엇이든 dict 목록으로 읽는다.

    형식을 넓게 받는 게 DB를 넓게 받는 길이다. psql --csv, mysql --json,
    mongoexport, bq --format=json, 스프레드시트 내보내기가 전부 이 넷 안에 있고,
    그러면 우리가 DB 드라이버를 하나도 더 안 붙여도 된다. 무엇보다 데이터가
    에이전트의 문맥을 거치지 않고 디스크에서 바로 온다.
    """
    with open(path, newline="") as f:
        text = f.read()
    if not text.strip():
        raise EventFileError(f"{path} is empty.")

    head = text.lstrip()[0]
    if head in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:       # JSONL — 한 줄에 객체 하나
            data = [json.loads(line) for line in text.splitlines() if line.strip()]
        if isinstance(data, dict):         # {"rows": [...]} / {"data": [...]} 형태
            data = next((v for v in data.values() if isinstance(v, list)), None)
        if not isinstance(data, list) or not data:
            raise EventFileError(f"{path} holds no list of rows.")
        return data

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


# 못 쓰는 행이 이 비율을 넘으면 '지저분한 데이터'가 아니라 '잘못된 컬럼'이다.
MAX_BAD_ROW_RATE = 0.1

# 이만큼 미래의 날짜는 데이터가 아니라 사고다 (테스트 계정, 잘못된 타임스탬프,
# 시간대 오류). 한 줄만 섞여도 today가 그리로 끌려가 전원이 이탈로 보고된다.
FUTURE_TOLERANCE_DAYS = 2


def load_events(csv_path: str) -> list[dict]:
    """이벤트 파일을 읽는다 — 형식과 컬럼명은 알아서 맞춘다.

    인자 이름이 csv_path인 건 역사적 이유다. CSV, TSV, JSONL 다 받는다.

    진짜 데이터는 지저분하다. 빈 칸 하나 때문에 5만 줄짜리 분석이 죽으면 안 되고,
    그렇다고 조용히 버려도 안 된다 — 몇 줄을 왜 버렸는지 세어서 알린다.
    """
    rows = _read_rows(csv_path)
    if not rows:
        raise EventFileError(f"{csv_path} has no rows.")
    cols = _match_columns(list(rows[0].keys()))

    horizon = date.today() + timedelta(days=FUTURE_TOLERANCE_DAYS)
    out: list[dict] = []
    skipped: dict[str, int] = defaultdict(int)
    for row in rows:
        uid = str(row.get(cols["user_id"]) or "").strip()
        ev = str(row.get(cols["event"]) or "").strip()
        raw = row.get(cols["date"])
        if not uid or not ev or raw in (None, ""):
            skipped["blank"] += 1
            continue
        try:
            day = parse_day(raw)
        except EventFileError:
            skipped["unreadable_date"] += 1
            continue
        if day > horizon:
            # 미래 날짜를 남기면 '오늘'이 그리로 끌려가 모두가 오래 잠든 것처럼 보인다
            skipped["future_date"] += 1
            continue
        out.append({
            "user_id": uid,
            "date": day,
            "event": ev,
            "platform": str(row.get(cols["platform"]) or "unknown") if "platform" in cols else "unknown",
        })

    total_bad = sum(skipped.values())
    if not out:
        raise EventFileError(
            f"Every row in {csv_path} was unusable ({dict(skipped)}). "
            "Check that the columns hold what their names suggest."
        )
    if total_bad > len(rows) * MAX_BAD_ROW_RATE:
        raise EventFileError(
            f"{total_bad} of {len(rows)} rows are unusable ({dict(skipped)}) — too many "
            "to be stray nulls. The columns are probably not the ones intended: "
            f"reading {cols['user_id']!r}, {cols['date']!r}, {cols['event']!r}."
        )
    if total_bad:
        out[0] = out[0] | {"_skipped": dict(skipped)}   # 리포트가 알릴 수 있게 남긴다
    return out


def skipped_rows(events: list[dict]) -> dict:
    """load_events가 버린 행 내역. 없으면 빈 dict."""
    return events[0].get("_skipped", {}) if events else {}


class ValueEventError(ValueError):
    """value_event가 데이터에 없거나 허영 지표일 때. 조용히 0%를 내지 않고 즉시 알린다."""


def check_value_event(events: list[dict], value_event: str) -> None:
    """분석 전에 value_event를 검증한다.

    오타 하나로 '이탈률 100%, 리텐션 0%' 리포트가 나가는 걸 막는 게 목적이다.
    (데이터에 없는 이벤트는 아무도 가치를 못 얻은 것처럼 계산되기 때문)
    """
    if is_vanity(value_event):
        raise ValueEventError(
            f"'{value_event}' is a vanity metric and can't be the value event. "
            "Opening an app is not the same as getting something out of it. "
            "Pick the action that means the user got what they came for "
            "(play_song, purchase, send_message)."
        )
    present = {e["event"] for e in events}
    if value_event not in present:
        options = sorted(e for e in present if not is_vanity(e))
        raise ValueEventError(
            f"'{value_event}' does not appear in this data. "
            f"Available events: {options or sorted(present)}"
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
        if len(active) <= 1 and tenure >= CHURN_JUDGEMENT_DAYS:
            buckets["churned"].append(u.user_id)
        elif active and all(d.weekday() >= 5 for d in active) and len(active) >= 2:
            buckets["weekend_only"].append(u.user_id)
        elif tenure >= REGULAR_JUDGEMENT_DAYS and len(recent2w) >= REGULAR_DAYS_IN_2W:
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


# "아하 모먼트를 찾았다"고 말할 기준 — 전/후 활동률이 이만큼은 올라야 한다.
# lift(집단 비교)가 아니라 behavior_change(같은 유저의 전/후)를 쓰는 이유는
# find_aha_moments 주석에 있다: 자주 오는 유저는 아무 행동이나 다 해서 lift를 부풀린다.
AHA_MIN_BEHAVIOR_CHANGE = 0.3


def top_aha(results: list[dict]) -> dict | None:
    """리포트가 아하 모먼트로 내세울 후보 하나. 없으면 None.

    이 판정은 여기서만 한다. 리포트 본문과 결론 문장이 서로 다른 기준을 쓰면
    "아하 모먼트 발견!" 카드 옆에 "뚜렷한 패턴이 없다"는 문장이 같이 나온다.
    """
    return next(
        (c for c in results if (c.get("behavior_change") or 0) >= AHA_MIN_BEHAVIOR_CHANGE),
        None,
    )


def audit_tracking(code_events: list[str], data_events: set[str] | None = None) -> dict:
    """코드에서 찾은 이벤트를 점검한다. 데이터가 있으면 대조까지 한다.

    data_events가 없어도 답할 게 있다 — 오히려 이 경우가 이 툴이 제일 필요한
    상황이다(추적을 안 해서 데이터가 없는 것). 코드만 봐도 "심어둔 게 전부
    허영 지표라 '유저가 가치를 얻었나'에 영원히 답할 수 없다"는 진단이 나온다.

    데이터가 있으면 추가로:
    - 코드에만 있음 → 심어놨는데 한 번도 안 찍힘 (고장이거나, 아무도 안 쓰는 기능)
    - 데이터에만 있음 → 코드에서 못 찾음 (죽은 코드거나, 스캔 누락)
    """
    code = set(code_events)
    usable = sorted(e for e in code if not is_vanity(e))
    out = {
        "in_code": sorted(code),
        "usable_in_code": usable,
        "vanity_in_code": sorted(e for e in code if is_vanity(e)),
        "can_measure_value": bool(usable),
    }
    if data_events is None:
        return out
    return out | {
        "tracked_ok": sorted(code & data_events),
        "in_code_never_fired": sorted(code - data_events),
        "in_data_not_in_code": sorted(data_events - code),
    }


def tracking_plan(code_events: list[str]) -> dict:
    """추적이 부족한 사람에게 줄 답: 지금 뭐가 부족하고, 언제 다시 오면 되는가.

    '며칠 뒤'는 지어낸 숫자가 아니라 판정 기준에서 그대로 나온다 —
    이탈은 CHURN_JUDGEMENT_DAYS, 단골과 1주차 리텐션은 REGULAR_JUDGEMENT_DAYS.
    """
    audit = audit_tracking(code_events)
    return audit | {
        "come_back_in_days": {
            "first_signal": CHURN_JUDGEMENT_DAYS,
            "full_picture": REGULAR_JUDGEMENT_DAYS,
        },
        "why_those_days": (
            f"Calling a user churned needs {CHURN_JUDGEMENT_DAYS} days of watching them; "
            f"calling one a regular, and week-1 retention, needs {REGULAR_JUDGEMENT_DAYS}. "
            "Before that the code has nothing honest to say."
        ),
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
