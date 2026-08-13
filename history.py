"""히스토리 — 분석 스냅샷을 로컬에 쌓아 "지난번 대비"를 만든다.

해자의 토대: 쓸수록 이 폴더에 그 서비스의 지표 역사가 쌓인다.
저장 위치: ./.dotplot/history.json (프로젝트 로컬 — 서버로 안 감)
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import date, datetime

import analysis

DEFAULT_DIR = ".dotplot"

# 스냅샷에 담는 핵심 지표 (리포트 비교 카드에 그대로 쓰임)
METRIC_KEYS = ["users", "regular_rate", "churned_rate", "w1_retention"]

# 지문에 담는 유저 수 상한. 이 도구는 유저 1,000명 미만을 위한 것이라
# 대부분은 전원이 들어간다. 넘으면 해시가 작은 순으로 잘라 표본으로 쓴다.
FINGERPRINT_CAP = 500

# 같은 서비스로 볼 겹침 비율 — 작은 쪽 기준 절반 이상이 같은 유저면 같은 데이터로 본다
SAME_DATASET_MIN_OVERLAP = 0.5


def user_fingerprint(users: dict) -> list[str]:
    """이 데이터가 '어느 서비스의 것'인지 나타내는 지문 — 유저 ID의 해시 목록.

    왜 필요한가: 같은 폴더에서 서비스를 두 개 분석하거나, 테스트 데이터로 한 번
    돌려본 뒤 진짜 데이터를 돌리면, value_event 이름만 같아도 서로 비교되어
    "지난주 대비 리텐션 -25%p" 같은 완전한 거짓 숫자가 리포트에 박힌다.

    왜 유저 ID인가: 지표(유저 수·기간)는 자랄 때마다 변하고, 이벤트 이름은
    서비스가 달라도 겹친다('purchase'). 반면 어떤 유저가 있었는지는
    데이터가 자라도 그대로 남아서, 겹침을 보면 같은 서비스인지 알 수 있다.

    ID는 해시해서 저장한다 — 이 파일에 원본 유저 ID를 남길 이유가 없다.
    """
    hashed = sorted(hashlib.sha256(uid.encode()).hexdigest()[:12] for uid in users)
    return hashed[:FINGERPRINT_CAP]


def same_dataset(a: list[str] | None, b: list[str] | None) -> bool:
    """두 지문이 같은 서비스의 것인가 — 작은 쪽 기준 겹침 비율로 판단.

    유저가 20명에서 200명으로 늘어도 원래 20명은 그대로 있으므로 겹침이 유지된다.
    조회 기간을 바꿔 일부만 뽑아도 마찬가지다. 다른 서비스면 겹침이 0이다.
    """
    if not a or not b:
        return False  # 지문 없는 옛 스냅샷 — 확인할 방법이 없으면 비교하지 않는다
    sa, sb = set(a), set(b)
    return len(sa & sb) / min(len(sa), len(sb)) >= SAME_DATASET_MIN_OVERLAP


def make_snapshot(users: dict, value_event: str, today: date) -> dict:
    buckets = analysis.classify_users(users, today)
    n = len(users)
    ret = analysis.retention_curve(users, today)
    w1 = next((r["rate"] for r in ret if r["week"] == 1), None)
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "data_end": today.isoformat(),
        "value_event": value_event,
        "dataset": user_fingerprint(users),
        "users": n,
        "regular_rate": round(len(buckets.get("regular", [])) / n, 3) if n else 0,
        "churned_rate": round(len(buckets.get("churned", [])) / n, 3) if n else 0,
        "w1_retention": w1,
    }


def _path(history_dir: str) -> str:
    return os.path.join(history_dir, "history.json")


def load_history(history_dir: str = DEFAULT_DIR) -> list[dict]:
    p = _path(history_dir)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return json.load(f)


def append_snapshot(snap: dict, history_dir: str = DEFAULT_DIR) -> str:
    os.makedirs(history_dir, exist_ok=True)
    hist = load_history(history_dir)
    hist.append(snap)
    with open(_path(history_dir), "w") as f:
        json.dump(hist, f, indent=1, ensure_ascii=False)
    return _path(history_dir)


def previous_snapshot(current: dict, history_dir: str = DEFAULT_DIR) -> dict | None:
    """비교 대상: 같은 데이터셋 · 같은 value_event · 다른 기준일(data_end)의 최근 스냅샷.

    셋 다 맞아야 한다:
      - dataset  같은 서비스여야 한다 (다르면 비교 자체가 거짓말)
      - value_event  같은 기준으로 잰 숫자여야 비교가 성립
      - data_end 다름  같은 데이터로 연달아 뽑을 때 자기 자신과 비교하지 않게

    dataset 키가 없는 옛 스냅샷은 건너뛴다 — 같은 서비스인지 확인할 방법이 없으면
    비교하지 않는 쪽이 맞다. 틀린 비교보다 비교 없음이 낫다.
    """
    for snap in reversed(load_history(history_dir)):
        if (
            same_dataset(snap.get("dataset"), current["dataset"])
            and snap["value_event"] == current["value_event"]
            and snap["data_end"] != current["data_end"]
        ):
            return snap
    return None


def diff(prev: dict, cur: dict) -> list[dict]:
    """비교 카드 재료: 지표별 전/후/변화. lower_is_better는 이탈률뿐."""
    rows = []
    for key in METRIC_KEYS:
        a, b = prev.get(key), cur.get(key)
        if a is None or b is None:
            continue
        rows.append({
            "key": key,
            "before": a,
            "after": b,
            "delta": round(b - a, 3),
            "good": (b - a) <= 0 if key == "churned_rate" else (b - a) >= 0,
        })
    return rows
