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
        "problem": "Nothing distinguished the users who stayed from the ones who left",
        "change": "Defined activation as 7 friends in 10 days and pointed all of onboarding at making connections",
        "result": "Users past that threshold retained far better; it became the company's north star",
        "source": "Chamath Palihapitiya, 'How We Put Facebook on the Path to 1 Billion Users' (talk)",
    },
    {
        "id": "twitter-follow-30",
        "company": "Twitter", "industry": "social", "stage": "growth",
        "patterns": ["high_day1_churn", "low_activation"],
        "problem": "New users saw an empty timeline and left",
        "change": "Pushed new users to follow 30 accounts during onboarding, so the first screen was never empty",
        "result": "Users who followed enough accounts came back far more often; this became a standard onboarding pattern",
        "source": "Josh Elman (Twitter growth at the time), various talks and interviews",
    },
    {
        "id": "slack-2000-messages",
        "company": "Slack", "industry": "b2b", "stage": "early",
        "patterns": ["aha_adoption", "low_regulars"],
        "problem": "No way to predict which free teams would convert and stay",
        "change": "Found that teams which exchanged 2,000 messages stuck, and made reaching that the goal of onboarding",
        "result": "Teams past 2,000 messages retained dramatically better — Slack's publicly cited activation bar",
        "source": "Stewart Butterfield interviews (First Round Review and others)",
    },
    {
        "id": "pinterest-simplified-onboarding",
        "company": "Pinterest", "industry": "content", "stage": "growth",
        "patterns": ["low_activation", "slow_time_to_value", "high_day1_churn"],
        "problem": "Most signups never reached the core action (saving a pin) in their first week",
        "change": "Cut onboarding down to picking interests and filling the feed immediately, removing steps before first value",
        "result": "New-user activation rose; widely shared as a reference activation fix",
        "source": "Casey Winters (former Pinterest growth lead), talks and blog",
    },
    {
        "id": "duolingo-streaks",
        "company": "Duolingo", "industry": "b2c", "stage": "growth",
        "patterns": ["low_regulars", "habit_context"],
        "problem": "Most learners studied for a few days and stopped",
        "change": "Focused on streaks and notifications — streak freezes, and repeated experiments on notification copy",
        "result": "Streak work was the main driver of the retention turnaround, documented publicly in detail",
        "source": "Duolingo blog; Jorge Mazal, 'How Duolingo reignited user growth' (Lenny's Newsletter)",
    },
    {
        "id": "calm-daily-reminder",
        "company": "Calm", "industry": "b2c", "stage": "early",
        "patterns": ["low_regulars", "aha_adoption", "habit_context"],
        "problem": "Users who never formed the habit drifted away quietly",
        "change": "Saw in the data that users who turned on a daily reminder retained far better, then prompted for it during onboarding",
        "result": "Retention improved markedly — a textbook case of spotting a correlation and then testing it",
        "source": "Sujan Patel interview, cited on Andrew Chen's blog",
    },
    {
        "id": "airbnb-photos",
        "company": "Airbnb", "industry": "commerce", "stage": "early",
        "patterns": ["low_activation", "slow_time_to_value"],
        "problem": "People browsed listings but didn't book",
        "change": "Replaced host photos with professional ones — the founders took the camera to New York themselves",
        "result": "Listings with professional photos booked noticeably more; it grew into a company-wide program",
        "source": "Y Combinator talk, Airbnb founding story (Brian Chesky)",
    },
    {
        "id": "superhuman-pmf-engine",
        "company": "Superhuman", "industry": "tool", "stage": "early",
        "patterns": ["low_regulars", "high_day1_churn"],
        "problem": "Retention stalled because it was unclear who the product was for",
        "change": "Surveyed for the users who would be very disappointed without it, then built only for that segment",
        "result": "Used the PMF score to steer the roadmap; the method itself became an industry standard",
        "source": "Rahul Vohra, 'How Superhuman Built an Engine to Find Product-Market Fit' (First Round Review)",
    },
    {
        "id": "groove-onboarding-email",
        "company": "Groove", "industry": "b2b", "stage": "early",
        "patterns": ["high_day1_churn", "slow_time_to_value"],
        "problem": "Users whose first session was short never came back",
        "change": "Used first-session behaviour to spot at-risk users and sent onboarding email timed to them",
        "result": "Conversion and retention improved for that segment; the process and numbers were published",
        "source": "Groove blog, 'How we reduced churn' series",
    },
    {
        "id": "dropbox-onboarding-checklist",
        "company": "Dropbox", "industry": "tool", "stage": "early",
        "patterns": ["low_activation", "aha_adoption"],
        "problem": "Users left before ever uploading a file, so they never saw the point",
        "change": "An onboarding checklist walked users to their first upload, rewarded with extra storage",
        "result": "More users reached the first upload — the aha action",
        "source": "Early Dropbox growth accounts — Sean Ellis interviews and others",
    },
    {
        "id": "zynga-day1-retention",
        "company": "Zynga", "industry": "game", "stage": "growth",
        "patterns": ["high_day1_churn"],
        "problem": "Most players never returned after day one",
        "change": "Made day-1 retention the company's top metric and designed the first session to create a reason to return tomorrow",
        "result": "Running on D1 became a core, publicly shared Zynga growth principle",
        "source": "Talks by former Zynga growth leaders (Andy Johns and others)",
    },
    {
        "id": "hubspot-activation-features",
        "company": "HubSpot", "industry": "b2b", "stage": "growth",
        "patterns": ["aha_adoption", "low_regulars"],
        "problem": "Hard to predict which new customers would churn",
        "change": "Found the combination of features retained customers used early, defined it as activation, and aimed onboarding and support at it",
        "result": "Reaching that bar predicted retention",
        "source": "HubSpot growth writing — Brian Balfour (former VP Growth), blog",
    },
    {
        "id": "amplitude-learn-method",
        "company": "(method)", "industry": "other", "stage": "early",
        "patterns": ["aha_adoption", "low_activation"],
        "problem": "With many aha candidates, no way to know which to believe",
        "change": "Three steps: compare retention of those who did the action against those who didn't, check each user's own before/after, then confirm with an A/B test",
        "result": "The standard route from correlation to cause — the method find_aha_moments follows",
        "source": "Amplitude's 'Mastering Retention' playbook, Reforge curriculum",
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
    top_aha = analysis.top_aha(aha)
    if top_aha and top_aha["did_count"] / n < 0.5:
        tags.add("aha_adoption")  # 아하 행동이 있는데 소수만 함 → 채택 기회
    return tags
