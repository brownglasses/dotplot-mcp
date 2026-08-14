"""데모가 절대 지나가지 않는 경로만 골라서 검사한다.

harness.py는 항상 4칸 샘플 CSV를, 항상 올바른 value_event로, 항상 저장소 안에서
돌린다. 그래서 예쁜 출력이 나와도 아래 경로들은 한 번도 실행되지 않는다 —
0.1.0에서 나간 버그 세 개가 전부 여기 있었다.
"""
from __future__ import annotations

import csv
from datetime import date, timedelta

import pytest

import analysis
import history
import report
from i18n import t as _t


def write_csv(path, rows, header):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    return str(path)


def events_for(users, days, event="purchase", prefix="u", start=date(2026, 7, 1)):
    return [
        [f"{prefix}{i:03d}", (start + timedelta(days=d)).isoformat(), event]
        for i in range(users)
        for d in range(days)
    ]


# ── README가 약속한 입력 ─────────────────────────────────────────────────

def test_three_column_csv_from_readme_works(tmp_path):
    """README Quick start가 안내하는 그대로의 3칸 CSV.

    샘플 데이터가 항상 platform 칸을 붙여서 만들기 때문에, 이 경로는 데모로는
    절대 안 밟힌다. 0.1.0은 여기서 KeyError로 죽었다.
    """
    path = write_csv(tmp_path / "e.csv", events_for(5, 10), ["user_id", "date", "event"])
    users = analysis.build_users(analysis.load_events(path), "purchase")
    assert len(users) == 5
    assert all(u.platform == "unknown" for u in users.values())


def test_platform_column_still_used_when_present(tmp_path):
    path = write_csv(
        tmp_path / "e.csv",
        [["u1", "ios", "2026-07-01", "purchase"]],
        ["user_id", "platform", "date", "event"],
    )
    users = analysis.build_users(analysis.load_events(path), "purchase")
    assert users["u1"].platform == "ios"


# ── 실패해야 하는 입력 ───────────────────────────────────────────────────

def test_value_event_missing_from_data_is_rejected(tmp_path):
    """오타난 이벤트 이름을 통과시키면 '이탈률 100%, 리텐션 0%'라는
    그럴듯한 거짓 리포트가 나간다. 조용한 성공이 제일 위험한 실패다."""
    path = write_csv(tmp_path / "e.csv", events_for(5, 10), ["user_id", "date", "event"])
    events = analysis.load_events(path)
    with pytest.raises(analysis.ValueEventError) as e:
        analysis.check_value_event(events, "purchasee")
    assert "purchase" in str(e.value)  # 고를 수 있는 이벤트를 알려줘야 한다


@pytest.mark.parametrize("vanity", ["open_app", "page_view", "session_start", "OPEN_APP"])
def test_vanity_value_event_is_rejected(tmp_path, vanity):
    rows = events_for(5, 10) + events_for(5, 10, event=vanity)
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    with pytest.raises(analysis.ValueEventError):
        analysis.check_value_event(analysis.load_events(path), vanity)


def test_valid_value_event_passes(tmp_path):
    path = write_csv(tmp_path / "e.csv", events_for(5, 10), ["user_id", "date", "event"])
    analysis.check_value_event(analysis.load_events(path), "purchase")  # 통과해야 함


# ── 같은 말이 두 뜻을 갖지 않는가 ────────────────────────────────────────

def test_regular_means_the_same_thing_everywhere(tmp_path):
    """classify_users와 find_aha_moments가 '단골'을 다르게 정의하면
    한 리포트 안에서 숫자가 서로 어긋난다."""
    rows = events_for(12, 30) + [["u000", "2026-07-05", "invite"]]
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    events = analysis.load_events(path)
    users = analysis.build_users(events, "purchase")
    today = max(e["date"] for e in events)

    from_classify = set(analysis.classify_users(users, today).get("regular", []))
    threshold = analysis.REGULAR_DAYS_IN_2W
    by_hand = {
        u.user_id for u in users.values()
        if sum(1 for d in u.value_days if (today - d).days < 14) >= threshold
        and (today - u.signup).days + 1 >= 14
    }
    assert from_classify == by_hand


# ── 히스토리가 남의 데이터와 비교하지 않는가 ─────────────────────────────

def snapshot(tmp_path, name, rows):
    path = write_csv(tmp_path / name, rows, ["user_id", "date", "event"])
    events = analysis.load_events(path)
    users = analysis.build_users(events, "purchase")
    return history.make_snapshot(users, "purchase", max(e["date"] for e in events))


def test_history_skips_a_different_service(tmp_path):
    """value_event 이름만 같으면 비교하던 버그 — 'purchase'는 흔한 이름이라
    서로 무관한 두 서비스가 '지난번 대비'로 엮였다."""
    mine = snapshot(tmp_path, "a.csv", events_for(20, 14, prefix="mine"))
    theirs = snapshot(tmp_path, "b.csv", events_for(20, 18, prefix="theirs"))
    assert not history.same_dataset(mine["dataset"], theirs["dataset"])


def test_history_follows_the_same_service_as_it_grows(tmp_path):
    """지문이 데이터 증가에 안 견디면 '지난번 대비' 기능 자체가 죽는다."""
    before = snapshot(tmp_path, "a.csv", events_for(20, 14))
    after = snapshot(tmp_path, "b.csv", events_for(50, 21))  # 유저 20 → 50
    assert history.same_dataset(before["dataset"], after["dataset"])


def test_history_ignores_snapshots_without_a_fingerprint():
    """지문 없는 옛 스냅샷은 같은 서비스인지 확인할 방법이 없다.
    틀린 비교보다 비교 없음이 낫다."""
    assert not history.same_dataset(None, ["abc"])
    assert not history.same_dataset([], ["abc"])


def test_fingerprint_holds_no_raw_user_ids(tmp_path):
    snap = snapshot(tmp_path, "a.csv", events_for(5, 10, prefix="alice"))
    assert not any("alice" in entry for entry in snap["dataset"])


# ── 리포트가 남의 데이터를 마크업으로 만들지 않는가 ──────────────────────

def test_report_escapes_user_data(tmp_path):
    """리포트는 publish_report로 공개 URL에 올라간다. 유저 ID나 이벤트 이름이
    그대로 마크업이 되면 안 된다."""
    hostile = '<img src=x onerror=alert(1)>'
    rows = events_for(6, 20) + [[hostile, "2026-07-02", "purchase"]] * 10
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    events = analysis.load_events(path)
    users = analysis.build_users(events, "purchase")
    today = max(e["date"] for e in events)

    html = report.render_html_report(users, min(e["date"] for e in events), 28, today)
    assert "onerror=alert" not in html
    assert "&lt;" in html  # 이스케이프된 흔적은 있어야 한다 (그냥 사라진 게 아니라)


# ── analyze: 정문 ────────────────────────────────────────────────────────

def test_analyze_without_data_routes_instead_of_failing(tmp_path):
    """데이터가 없다고 죽으면 안 된다. 다음에 뭘 할지 알려줘야 한다."""
    import server
    r = server.analyze()
    assert r["status"] == "need_data"
    assert any("load_from_db" in step for step in r["what_to_do"])


def test_analyze_picks_a_value_event_and_reports_alternatives(tmp_path):
    import server
    rows = (
        events_for(10, 25, event="purchase")
        + events_for(10, 25, event="open_app")       # 허영 — 골라선 안 됨
        + events_for(2, 2, event="refund")           # 너무 드묾 — 골라선 안 됨
    )
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    r = server.analyze(path, output_path=str(tmp_path / "r.html"))
    assert r["status"] == "ok"
    assert r["value_event"]["chosen"] == "purchase"
    assert "open_app" not in r["value_event"]["others_available"]


def test_analyze_honours_an_explicit_value_event(tmp_path):
    """에이전트는 코드를 읽었으므로 의미를 안다 — 그 판단이 코드보다 우선해야 한다."""
    import server
    rows = events_for(10, 25, event="view_item") + events_for(10, 20, event="purchase")
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    r = server.analyze(path, value_event="purchase", output_path=str(tmp_path / "r.html"))
    assert r["value_event"]["chosen"] == "purchase"


def test_analyze_says_so_when_nothing_is_trackable(tmp_path):
    import server
    path = write_csv(tmp_path / "e.csv", events_for(10, 20, event="page_view"),
                     ["user_id", "date", "event"])
    r = server.analyze(path, output_path=str(tmp_path / "r.html"))
    assert r["status"] == "no_value_event"


def test_report_never_contradicts_itself_about_the_aha_moment(tmp_path):
    """아하 카드를 띄우면서 '뚜렷한 패턴 없음'이라고 쓰면 안 된다 —
    두 판정이 서로 다른 기준을 쓰면 그런 리포트가 나온다."""
    import server
    rows = events_for(12, 30, event="purchase") + [
        [f"u{i:03d}", "2026-07-08", "invite_friend"] for i in range(8)
    ]
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    out = tmp_path / "r.html"
    r = server.analyze(path, output_path=str(out))
    html = out.read_text()
    shows_card = "aha.title" not in html and "💡" in html
    says_nothing_found = _t("en", "insight.none") in html
    assert not (shows_card and says_nothing_found)
    if r["aha_moment"]:
        assert not says_nothing_found


# ── 언어 경계 ────────────────────────────────────────────────────────────

def test_tool_descriptions_and_returns_are_english(tmp_path):
    """에이전트가 읽는 글과 반환값 키는 영어여야 한다 — 사용자는 전 세계에 있다.
    (사람에게 보일 문장은 i18n으로 가고, 코드 주석은 한국어 그대로 둔다.)"""
    import re
    import server
    korean = re.compile(r"[가-힣]")

    tools = [getattr(server, n) for n in dir(server) if not n.startswith("_")]
    for fn in tools:
        doc = getattr(fn, "__doc__", None)
        if callable(fn) and doc and getattr(fn, "__module__", "") == "server":
            assert not korean.search(doc), f"{fn.__name__} 설명문에 한글이 있다"

    path = write_csv(tmp_path / "e.csv", events_for(8, 20), ["user_id", "date", "event"])
    out = server.analyze(path, output_path=str(tmp_path / "r.html"))
    assert not korean.search(repr(list(out)))


def test_reports_still_speak_the_users_language(tmp_path):
    """영어로 정리했다고 리포트까지 영어가 되면 안 된다 — 그건 i18n의 몫이다."""
    import server
    path = write_csv(tmp_path / "e.csv", events_for(8, 20), ["user_id", "date", "event"])
    labels = server.classify_users(path, "purchase", lang="ko")
    assert any("가" <= ch <= "힣" for v in labels.values() for ch in v["label"])


# ── 어떤 도구가 뱉은 파일이든 읽는가 ─────────────────────────────────────

def rows_as(fmt, tmp_path, user_key, date_key, event_key, date_fn):
    import json
    rows = [{user_key: f"u{i:03d}", date_key: date_fn(d), event_key: "purchase"}
            for i in range(8) for d in range(20)]
    p = tmp_path / f"e.{fmt}"
    if fmt == "json":
        p.write_text(json.dumps(rows))
    elif fmt == "jsonl":
        p.write_text("\n".join(json.dumps(r) for r in rows))
    elif fmt == "bq":                      # {"rows": [...]}
        p = tmp_path / "e.json"
        p.write_text(json.dumps({"rows": rows}))
    else:
        sep = "\t" if fmt == "tsv" else ","
        head = sep.join([user_key, date_key, event_key])
        body = "\n".join(sep.join(str(r[k]) for k in (user_key, date_key, event_key)) for r in rows)
        p.write_text(head + "\n" + body + "\n")
    return str(p)


@pytest.mark.parametrize("fmt,ukey,dkey,ekey,dfn", [
    # psql --csv: 원본 컬럼명 + 타임스탬프
    ("csv",   "user_id",     "created_at",  "event_name", lambda d: f"2026-07-{d+1:02d} 14:23:11"),
    # mysql --json
    ("json",  "uid",         "ts",          "action",     lambda d: f"2026-07-{d+1:02d}T09:00:00Z"),
    # mongoexport
    ("jsonl", "customer_id", "occurred_at", "type",        lambda d: f"2026-07-{d+1:02d}T09:00:00+09:00"),
    # bq --format=json: epoch 밀리초
    ("bq",    "user",        "timestamp",   "event",       lambda d: 1782950400000 + d * 86400000),
    # 스프레드시트 내보내기
    ("tsv",   "User",        "Day",         "Action",      lambda d: f"2026/07/{d+1:02d}"),
])
def test_reads_what_other_tools_export(tmp_path, fmt, ukey, dkey, ekey, dfn):
    """DB를 넓게 지원하는 길은 드라이버를 늘리는 게 아니라, 이미 있는 도구가
    뱉은 파일을 읽는 것이다. 그래야 데이터가 에이전트 문맥을 거치지 않는다."""
    path = rows_as(fmt, tmp_path, ukey, dkey, ekey, dfn)
    events = analysis.load_events(path)
    assert len({e["user_id"] for e in events}) == 8
    assert all(isinstance(e["date"], date) for e in events)


@pytest.mark.parametrize("bad", ["07/01/2026", "next tuesday", ""])
def test_ambiguous_dates_are_refused_not_guessed(bad):
    """07/01/2026이 7월 1일인지 1월 7일인지 코드는 모른다.
    찍으면 조용히 틀린 리포트가 된다."""
    with pytest.raises(analysis.EventFileError):
        analysis.parse_day(bad)


def test_unmatched_columns_say_what_to_do(tmp_path):
    path = write_csv(tmp_path / "e.csv", [["1", "2", "3"]], ["a", "b", "c"])
    with pytest.raises(analysis.EventFileError) as e:
        analysis.load_events(path)
    assert "a" in str(e.value) and "AS date" in str(e.value)


# ── 추적이 없는 사람도 들어올 수 있는가 ──────────────────────────────────

def test_audit_tracking_works_without_any_data():
    """추적을 안 해서 온 사람인데 데이터를 요구하면 안 된다 — 이 툴이 제일
    필요한 상황이 바로 데이터가 없는 상황이다."""
    import server
    r = server.audit_tracking(["open_app", "page_view"])
    assert r["can_measure_value"] is False
    assert r["vanity_in_code"] == ["open_app", "page_view"]
    assert r["come_back_in_days"]["first_signal"] == analysis.CHURN_JUDGEMENT_DAYS
    assert r["come_back_in_days"]["full_picture"] == analysis.REGULAR_JUDGEMENT_DAYS


def test_audit_tracking_still_compares_when_data_exists(tmp_path):
    import server
    path = write_csv(tmp_path / "e.csv", events_for(6, 10), ["user_id", "date", "event"])
    r = server.audit_tracking(["purchase", "share"], path)
    assert r["tracked_ok"] == ["purchase"]
    assert r["in_code_never_fired"] == ["share"]


def test_come_back_days_come_from_the_judgement_thresholds():
    """'며칠 뒤 오세요'가 지어낸 숫자면 안 된다. 유저를 그만큼 지켜봐야
    이탈·단골을 판정할 수 있다는 코드의 기준에서 나와야 한다."""
    plan = analysis.tracking_plan(["purchase"])
    assert plan["come_back_in_days"] == {
        "first_signal": analysis.CHURN_JUDGEMENT_DAYS,
        "full_picture": analysis.REGULAR_JUDGEMENT_DAYS,
    }
    assert plan["can_measure_value"] is True


def test_analyze_sends_a_trackless_project_somewhere_reachable(tmp_path):
    """막다른 길로 안내하면 안 된다 — analyze가 가리키는 곳이 실제로 열려 있어야."""
    import server
    for guidance in (
        " ".join(server.analyze()["what_to_do"]),
        server.analyze(
            write_csv(tmp_path / "e.csv", events_for(9, 20, event="page_view"),
                      ["user_id", "date", "event"]),
            output_path=str(tmp_path / "r.html"),
        )["what_to_do"],
    ):
        assert "audit_tracking" in guidance
    server.audit_tracking(["page_view"])   # 안내받은 대로 부르면 열려야 한다


# ── 진짜 데이터는 지저분하다 ─────────────────────────────────────────────

def test_a_few_bad_rows_do_not_kill_the_analysis(tmp_path):
    """빈 칸 하나 때문에 5만 줄짜리 분석이 죽으면 안 된다.
    production 내보내기에 NULL은 늘 있다."""
    rows = events_for(12, 20) + [["", "2026-07-05", "purchase"],
                                 ["u001", "", "purchase"],
                                 ["u002", "2026-07-05", ""]]
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    events = analysis.load_events(path)
    assert len({e["user_id"] for e in events}) == 12
    assert analysis.skipped_rows(events) == {"blank": 3}


def test_a_future_dated_row_cannot_make_everyone_look_dormant(tmp_path):
    """'오늘'은 데이터의 마지막 날이다. 테스트 계정 하나가 2099년으로 찍히면
    모든 유저가 몇 십 년 잠든 것처럼 계산돼 단골이 전부 사라진다."""
    clean = write_csv(tmp_path / "a.csv", events_for(12, 20), ["user_id", "date", "event"])
    dirty = write_csv(tmp_path / "b.csv",
                      events_for(12, 20) + [["u001", "2099-01-01", "purchase"]],
                      ["user_id", "date", "event"])

    def buckets(p):
        ev = analysis.load_events(p)
        u = analysis.build_users(ev, "purchase")
        return {k: len(v) for k, v in analysis.classify_users(u, max(e["date"] for e in ev)).items()}

    assert buckets(clean) == buckets(dirty)
    assert analysis.skipped_rows(analysis.load_events(dirty)) == {"future_date": 1}


def test_mostly_broken_data_is_refused_not_silently_trimmed(tmp_path):
    """빈 칸 몇 개는 지저분한 데이터지만, 절반이 비어 있으면 컬럼을 잘못 잡은 것이다.
    그건 조용히 버리면 안 되고 멈춰야 한다."""
    rows = events_for(3, 5) + [["", "", ""] for _ in range(30)]
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    with pytest.raises(analysis.EventFileError) as e:
        analysis.load_events(path)
    assert "too many" in str(e.value)


def test_analyze_reports_what_it_dropped(tmp_path):
    """버린 행을 조용히 숨기면 그것도 거짓말이다."""
    import server
    rows = events_for(12, 20) + [["u001", "2099-01-01", "purchase"]]
    path = write_csv(tmp_path / "e.csv", rows, ["user_id", "date", "event"])
    r = server.analyze(path, output_path=str(tmp_path / "r.html"))
    assert r["skipped_rows"] == {"future_date": 1}
