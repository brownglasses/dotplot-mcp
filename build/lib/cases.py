"""사례 도서관 v0 — 공개 자료에서 큐레이션한 리텐션/활성화 개선 사례.

원칙:
  - 전부 공개된 강연·아티클·인터뷰에서 나온 사례 (출처 명시)
  - 숫자가 2차 인용이라 불확실한 것은 정성적으로 기술 (숫자를 지어내지 않는다)
  - pattern 태그는 우리 진단 코드가 내는 태그와 같은 어휘 → 자동 매칭

사용자 옵트인 사례(git 대조 자동 수집)가 쌓이면 이 위에 얹는다.
"""
from __future__ import annotations

from datetime import date

# 진단 태그 어휘 (find_similar_cases가 계산해서 붙임)
#   high_day1_churn     첫날 이후 안 돌아오는 유저가 많음
#   low_activation      가입은 하는데 첫 가치 경험을 못 함
#   slow_time_to_value  첫 가치까지 걸리는 시간이 김
#   aha_adoption        아하 행동이 발견됐는데 하는 유저가 적음
#   low_regulars        습관 사용자(찐팬) 비율이 낮음
#   habit_context       특정 요일/상황에서만 쓰는 패턴

CASES = [
    {
        "id": "facebook-7-friends",
        "company": "Facebook", "industry": "social", "stage": "growth",
        "patterns": ["aha_adoption", "high_day1_churn", "low_regulars"],
        "problem": "가입 후 이탈하는 유저와 남는 유저를 가르는 요인을 몰랐다",
        "change": "'10일 안에 친구 7명'을 활성화 지표로 정의하고, 온보딩 전체를 친구 연결에 집중",
        "result": "이 임계점을 넘은 유저의 잔존율이 확연히 높았고, 회사 전체의 북극성 지표가 됨",
        "source": "Chamath Palihapitiya, 'How We Put Facebook on the Path to 1 Billion Users' (강연)",
    },
    {
        "id": "twitter-follow-30",
        "company": "Twitter", "industry": "social", "stage": "growth",
        "patterns": ["high_day1_churn", "low_activation"],
        "problem": "가입자가 텅 빈 타임라인을 보고 떠났다",
        "change": "온보딩에서 계정 30개를 팔로우하게 유도 — 첫 화면이 비어 있지 않게",
        "result": "충분히 팔로우한 유저의 재방문율이 유의미하게 높아, 온보딩 표준이 됨",
        "source": "Josh Elman (당시 Twitter 그로스), 여러 강연·인터뷰",
    },
    {
        "id": "slack-2000-messages",
        "company": "Slack", "industry": "b2b", "stage": "early",
        "patterns": ["aha_adoption", "low_regulars"],
        "problem": "무료 팀 중 어느 팀이 유료로 남을지 예측이 안 됐다",
        "change": "'팀이 메시지 2,000개를 주고받으면 정착한다'를 발견, 그 임계점 도달을 온보딩 목표로",
        "result": "2,000개를 넘긴 팀의 잔존이 극적으로 높음 — Slack의 공개된 활성화 기준",
        "source": "Stewart Butterfield 인터뷰 (First Round Review 외)",
    },
    {
        "id": "pinterest-simplified-onboarding",
        "company": "Pinterest", "industry": "content", "stage": "growth",
        "patterns": ["low_activation", "slow_time_to_value", "high_day1_churn"],
        "problem": "가입자 다수가 첫 주에 핵심 행동(핀 저장)까지 못 갔다",
        "change": "온보딩을 관심사 선택 → 즉시 피드 채움으로 단순화, 첫 가치까지의 단계를 줄임",
        "result": "신규 유저 활성화율 상승 — 그로스팀의 대표적 활성화 개선 사례로 공유됨",
        "source": "Casey Winters (전 Pinterest 그로스 리드) 강연·블로그",
    },
    {
        "id": "duolingo-streaks",
        "company": "Duolingo", "industry": "b2c", "stage": "growth",
        "patterns": ["low_regulars", "habit_context"],
        "problem": "학습을 며칠 하다 끊는 유저가 대부분이었다",
        "change": "스트릭(연속 학습)과 알림 최적화에 집중 — 스트릭 보호 아이템, 알림 문구 실험 반복",
        "result": "스트릭 관련 개선이 리텐션을 끌어올린 핵심 동력 (공개적으로 상세히 문서화됨)",
        "source": "Duolingo 블로그, Jorge Mazal 'How Duolingo reignited user growth' (Lenny's Newsletter)",
    },
    {
        "id": "calm-daily-reminder",
        "company": "Calm", "industry": "b2c", "stage": "early",
        "patterns": ["low_regulars", "aha_adoption", "habit_context"],
        "problem": "명상 앱 특성상 습관이 안 붙은 유저가 조용히 떠났다",
        "change": "데이터에서 '데일리 리마인더를 켠 유저는 잔존이 훨씬 높다'를 발견, 온보딩에서 리마인더 설정을 유도",
        "result": "리마인더 설정 유도가 리텐션을 크게 개선 — 상관관계 발견 → 실험 검증의 교과서 사례",
        "source": "Sujan Patel 인터뷰, Andrew Chen 블로그에서 인용",
    },
    {
        "id": "airbnb-photos",
        "company": "Airbnb", "industry": "commerce", "stage": "early",
        "patterns": ["low_activation", "slow_time_to_value"],
        "problem": "숙소를 봐도 예약(첫 가치)으로 이어지지 않았다",
        "change": "호스트 숙소를 전문 사진으로 교체 (창업자가 직접 카메라 들고 뉴욕 방문)",
        "result": "전문 사진 숙소의 예약이 눈에 띄게 증가, 전사 프로그램으로 확대",
        "source": "Y Combinator 강연, Airbnb 창업 스토리 (Brian Chesky)",
    },
    {
        "id": "superhuman-pmf-engine",
        "company": "Superhuman", "industry": "tool", "stage": "early",
        "patterns": ["low_regulars", "high_day1_churn"],
        "problem": "누구를 위해 만들고 있는지가 흐려서 리텐션이 정체됐다",
        "change": "'이 제품이 사라지면 매우 실망할 사람'을 설문으로 찾고, 그 세그먼트가 사랑하는 것에만 집중",
        "result": "PMF 점수를 지표로 삼아 제품 방향을 재정렬 — 방법론 자체가 업계 표준이 됨",
        "source": "Rahul Vohra, 'How Superhuman Built an Engine to Find Product-Market Fit' (First Round Review)",
    },
    {
        "id": "groove-onboarding-email",
        "company": "Groove", "industry": "b2b", "stage": "early",
        "patterns": ["high_day1_churn", "slow_time_to_value"],
        "problem": "가입 후 첫 세션이 짧은 유저가 그대로 이탈했다",
        "change": "첫 세션 행동 데이터로 이탈 위험 유저를 찾아, 시점 맞춘 온보딩 이메일 발송",
        "result": "위험 세그먼트의 전환·잔존이 개선 — 블로그에 과정과 수치를 공개",
        "source": "Groove 블로그 'How we reduced churn' 시리즈",
    },
    {
        "id": "dropbox-onboarding-checklist",
        "company": "Dropbox", "industry": "tool", "stage": "early",
        "patterns": ["low_activation", "aha_adoption"],
        "problem": "가입자가 파일을 올려보기 전에 떠났다 — 첫 가치 미경험",
        "change": "온보딩 체크리스트로 '파일 1개 넣기'까지를 안내 (+ 완료 시 용량 보상)",
        "result": "첫 파일 업로드(아하 행동)까지 도달하는 유저 비율 상승",
        "source": "Dropbox 초기 그로스 사례 — Sean Ellis 인터뷰 등",
    },
    {
        "id": "zynga-day1-retention",
        "company": "Zynga", "industry": "game", "stage": "growth",
        "patterns": ["high_day1_churn"],
        "problem": "게임 유저의 대부분이 첫날 이후 돌아오지 않았다",
        "change": "D1 리텐션을 조직의 최우선 지표로 — 첫 세션에서 '내일 돌아올 이유'를 만들게 게임 설계",
        "result": "D1 중심 운영이 Zynga 그로스의 핵심 원칙으로 공개 공유됨",
        "source": "Zynga 출신 그로스 리더들 강연 (Andy Johns 외)",
    },
    {
        "id": "hubspot-activation-features",
        "company": "HubSpot", "industry": "b2b", "stage": "growth",
        "patterns": ["aha_adoption", "low_regulars"],
        "problem": "어떤 신규 고객이 이탈할지 예측하기 어려웠다",
        "change": "잔존 고객이 초기에 쓰는 기능 조합을 찾아 '활성화 기준'으로 정의, CS/온보딩을 거기 정렬",
        "result": "활성화 기준 도달률이 잔존 예측 지표로 작동",
        "source": "HubSpot 그로스 사례 — Brian Balfour(전 HubSpot VP Growth) 블로그",
    },
    {
        "id": "amplitude-learn-method",
        "company": "(방법론)", "industry": "other", "stage": "early",
        "patterns": ["aha_adoption", "low_activation"],
        "problem": "아하 모먼트 후보가 많을 때 뭘 믿어야 할지 모름",
        "change": "행동을 한 집단 vs 안 한 집단의 잔존 비교 + '그 행동 전후' 변화 확인 + A/B로 검증하는 3단계",
        "result": "상관→인과 확인의 표준 절차 (이 도구의 find_aha_moments가 따르는 방법)",
        "source": "Amplitude 'Mastering Retention' 플레이북, Reforge 커리큘럼",
    },
]


def match_cases(tags: set[str], industry: str | None = None, top: int = 4) -> list[dict]:
    """진단 태그와 겹치는 사례를 점수순으로 반환. 같은 업종이면 가산점."""
    scored = []
    for c in CASES:
        overlap = tags & set(c["patterns"])
        if not overlap:
            continue
        score = len(overlap) + (0.5 if industry and c["industry"] == industry else 0)
        scored.append((score, sorted(overlap), c))
    scored.sort(key=lambda x: -x[0])
    return [
        {**c, "matched_on": overlap}
        for _, overlap, c in scored[:top]
    ]


def diagnose_tags(users: dict, events: list[dict], value_event: str, today: date) -> set[str]:
    """우리 진단 결과를 사례 태그 어휘로 변환 — 전부 코드, LLM 없음."""
    import analysis

    tags: set[str] = set()
    n = len(users)
    buckets = analysis.classify_users(users, today)
    funnel = analysis.onboarding_funnel(users, today)
    aha = analysis.find_aha_moments(events, users, value_event, today)

    if len(buckets.get("churned", [])) / n >= 0.25:
        tags.add("high_day1_churn")
    steps = {s["key"]: s["count"] for s in funnel["steps"]}
    if steps["first_value"] < steps["signup"] * 0.8:
        tags.add("low_activation")
    if (funnel["median_days_to_value"] or 0) >= 3:
        tags.add("slow_time_to_value")
    if len(buckets.get("regular", [])) / n < 0.25:
        tags.add("low_regulars")
    if len(buckets.get("weekend_only", [])) / n >= 0.15:
        tags.add("habit_context")
    top_aha = next((c for c in aha if (c["behavior_change"] or 0) >= 0.3), None)
    if top_aha and top_aha["did_count"] / n < 0.5:
        tags.add("aha_adoption")  # 아하 행동이 있는데 소수만 함 → 채택 기회
    return tags
