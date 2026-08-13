"""익명 벤치마크 — 옵트인 수집 + 비교.

프라이버시 설계 (이게 신뢰의 전부다):
  - 서버로 가는 것: 집계값 5개뿐 (이탈률, 주말비율, 단골률, 아하 lift, 유저 수)
  - 절대 안 가는 것: 유저 ID, 이벤트 로그, 날짜, 서비스 이름, 그 어떤 원본 데이터도
  - 백엔드 권한: 익명 키로는 INSERT만 가능. 남의 제출을 읽는 방법이 없음
  - 비교 조회: get_benchmark() 함수가 백분위 통계만 반환. 개별 행 접근 불가
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date

from analysis import UserRow, classify_users, find_aha_moments

# 공개 엔드포인트 — publishable 키는 공개용으로 설계된 키다 (INSERT-only RLS로 보호)
BENCH_URL = os.environ.get("DOTPLOT_BENCH_URL", "https://nwnmcwlurtduwhxomgxz.supabase.co")
BENCH_KEY = os.environ.get(
    "DOTPLOT_BENCH_KEY", "sb_publishable_pkaIX60tfZqg7iEs0c3brQ_yqBIg7r9"
)

INDUSTRIES = ["b2c", "b2b", "commerce", "content", "social", "tool", "game", "other"]
STAGES = ["pre_launch", "under_100_users", "under_1k_users", "over_1k_users"]


def compute_aggregates(
    events: list[dict], users: dict[str, UserRow], value_event: str, today: date
) -> dict:
    """제출할 집계값을 계산한다 — 이 함수의 반환값이 서버로 가는 전부다."""
    n = len(users)
    buckets = classify_users(users, today)
    rate = lambda key: len(buckets.get(key, [])) / n
    aha = find_aha_moments(events, users, value_event, today)
    return {
        "users_count": n,
        "churned_rate": round(rate("churned"), 3),
        "weekend_rate": round(rate("weekend_only"), 3),
        "regular_rate": round(rate("regular"), 3),
        "aha_lift": aha[0]["lift"] if aha else None,
    }


def _request(path: str, payload: dict) -> dict | list | None:
    req = urllib.request.Request(
        f"{BENCH_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={
            "apikey": BENCH_KEY,
            "Authorization": f"Bearer {BENCH_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read().decode()
        return json.loads(body) if body else None


def submit(aggregates: dict, industry: str, stage: str) -> None:
    _request("/rest/v1/benchmark_submissions", {**aggregates, "industry": industry, "stage": stage})


def fetch(industry: str, stage: str) -> dict:
    """백분위 통계를 가져온다.

    RPC가 TABLE/SETOF로 정의돼 있으면 PostgREST가 행 배열을 주고,
    스칼라 JSON이면 객체를 준다 — 호출부가 항상 dict를 받도록 여기서 맞춘다.
    """
    res = _request("/rest/v1/rpc/get_benchmark", {"p_industry": industry, "p_stage": stage})
    if isinstance(res, list):
        res = res[0] if res else {}
    return res if isinstance(res, dict) else {}
