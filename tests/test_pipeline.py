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
