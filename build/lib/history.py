"""히스토리 — 분석 스냅샷을 로컬에 쌓아 "지난번 대비"를 만든다.

해자의 토대: 쓸수록 이 폴더에 그 서비스의 지표 역사가 쌓인다.
저장 위치: ./.dotplot/history.json (프로젝트 로컬 — 서버로 안 감)
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime

import analysis

DEFAULT_DIR = ".dotplot"

# 스냅샷에 담는 핵심 지표 (리포트 비교 카드에 그대로 쓰임)
METRIC_KEYS = ["users", "regular_rate", "churned_rate", "w1_retention"]


def make_snapshot(users: dict, value_event: str, today: date) -> dict:
    buckets = analysis.classify_users(users, today)
    n = len(users)
    ret = analysis.retention_curve(users, today)
    w1 = next((r["rate"] for r in ret if r["week"] == 1), None)
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "data_end": today.isoformat(),
        "value_event": value_event,
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
    """비교 대상: 같은 value_event이면서 데이터 기준일(data_end)이 다른 가장 최근 스냅샷.
    (같은 데이터로 리포트를 연달아 뽑아도 자기 자신과 비교하지 않게)"""
    for snap in reversed(load_history(history_dir)):
        if snap["value_event"] == current["value_event"] and snap["data_end"] != current["data_end"]:
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
