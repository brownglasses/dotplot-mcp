"""다국어 문자열 — 사용자 눈에 닿는 모든 문장은 여기서만 나온다.

새 언어 추가 방법: STRINGS에 언어 코드 하나 추가하고 같은 키를 번역하면 끝.
키가 빠지면 영어로 폴백된다.
"""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # 유저 패턴 분류
        "bucket.churned": "Used once, never returned (onboarding issue?)",
        "bucket.weekend_only": "Weekend-only",
        "bucket.regular": "Almost daily (core fans)",
        "bucket.casual": "Occasional",
        # 도트 플롯
        "weekdays": "M,T,W,TH,F,SA,S",
        # HTML 리포트
        "report.title": "Are our users actually using it?",
        "report.subtitle": "One row = one user · one cell = one day (from {start})",
        "report.legend.active": "Active day",
        "report.legend.first": "First day",
        "report.legend.weekend_user": "Weekend-only user",
        "report.glance": "At a glance",
        "report.glance_item": "<b>{n} users</b> — {label}",
        "report.insights_title": "So, what should we do?",
        "report.insights_note": "* Auto-computed, for reference only. Verify causation with an experiment.",
        "report.index_title": "Dot Plot Reports",
        "report.index_body": "Reports are accessible only via issued links.",
        # 규칙 기반 인사이트
        "insight.aha": (
            "💡 <b>{name}</b> — {did} users did it and <b>{rate_did}</b> became regulars. "
            "Only {rate_not} of those who didn't. "
            "→ Nudge new users to do this right after signup, then verify it's causal."
        ),
        "insight.churn": (
            "⚠️ <b>{churned} of {total} users ({pct})</b> never came back after their first day. "
            "→ Review the first-day (onboarding) experience."
        ),
        "insight.weekend": (
            "📅 <b>{n} users</b> only show up on weekends. "
            "→ Ask one of them directly what blocks weekday use."
        ),
        "insight.none": "No clear pattern yet. Check again once more data accumulates.",
        # 온보딩 퍼널
        "funnel.title": "Where do new users drop off?",
        "funnel.signup": "Signed up",
        "funnel.first_value": "Got first value",
        "funnel.returned": "Came back another day",
        "funnel.recent": "Active in last 2 weeks",
        "funnel.median_days": "Median time from signup to first value: {days} day(s)",
        # 리텐션 커브
        "retention.title": "Weekly retention",
        "retention.subtitle": "% of users active in week N after their signup",
        "retention.week": "W{n}",
        # 히스토리 (지난번 대비)
        "history.title": "Since the last report ({date})",
        "history.users": "Users",
        "history.regular_rate": "Core fans",
        "history.churned_rate": "Churned after day one",
        "history.w1_retention": "Week-1 retention",
    },
    "ko": {
        "bucket.churned": "한번 쓰고 떠남 (온보딩 의심)",
        "bucket.weekend_only": "주말에만 씀",
        "bucket.regular": "거의 매일 씀 (찐팬)",
        "bucket.casual": "가끔 씀",
        "weekdays": "월,화,수,목,금,토,일",
        "report.title": "우리 유저들, 진짜로 쓰고 있나?",
        "report.subtitle": "한 줄 = 유저 한 명 · 한 칸 = 하루 ({start} ~)",
        "report.legend.active": "쓴 날",
        "report.legend.first": "처음 쓴 날",
        "report.legend.weekend_user": "주말에만 쓰는 유저",
        "report.glance": "한눈에 보기",
        "report.glance_item": "<b>{n}명</b> — {label}",
        "report.insights_title": "그래서, 뭘 하면 될까?",
        "report.insights_note": "* 자동 계산된 참고용이에요. 인과관계는 실험으로 확인하세요.",
        "report.index_title": "Dot Plot Reports",
        "report.index_body": "리포트는 발급받은 링크로만 접근할 수 있어요.",
        "insight.aha": (
            "💡 <b>{name}</b>을(를) 한 유저 {did}명 중 <b>{rate_did}</b>가 단골이 됐어요. "
            "안 한 유저는 {rate_not}뿐이에요. "
            "→ 가입 직후에 이걸 하게 유도하고, 효과가 진짜인지 확인해보세요."
        ),
        "insight.churn": (
            "⚠️ 전체 {total}명 중 <b>{churned}명({pct})</b>이 첫날 이후 돌아오지 않았어요. "
            "→ 첫날 경험(온보딩)을 점검해보세요."
        ),
        "insight.weekend": (
            "📅 <b>{n}명</b>은 주말에만 써요. "
            "→ 주중 사용을 막는 게 뭔지, 그 유저 한 명에게 직접 물어보세요."
        ),
        "insight.none": "아직 뚜렷한 패턴이 없어요. 데이터가 더 쌓이면 다시 확인해보세요.",
        "funnel.title": "새 유저는 어디서 이탈하나?",
        "funnel.signup": "가입",
        "funnel.first_value": "첫 가치 경험",
        "funnel.returned": "다른 날 재방문",
        "funnel.recent": "최근 2주 내 활동",
        "funnel.median_days": "가입 → 첫 가치까지 걸린 시간(중앙값): {days}일",
        "retention.title": "주차별 리텐션",
        "retention.subtitle": "가입 후 N주차에 활동한 유저 비율",
        "retention.week": "{n}주",
        "history.title": "지난 리포트({date}) 대비",
        "history.users": "유저 수",
        "history.regular_rate": "찐팬 비율",
        "history.churned_rate": "첫날 이탈률",
        "history.w1_retention": "1주차 리텐션",
    },
    "ja": {
        "bucket.churned": "一度使って離脱 (オンボーディングに問題?)",
        "bucket.weekend_only": "週末のみ利用",
        "bucket.regular": "ほぼ毎日利用 (コアファン)",
        "bucket.casual": "たまに利用",
        "weekdays": "月,火,水,木,金,土,日",
        "report.title": "ユーザーは本当に使っている?",
        "report.subtitle": "1行 = 1ユーザー · 1マス = 1日 ({start} ~)",
        "report.legend.active": "利用した日",
        "report.legend.first": "初回利用日",
        "report.legend.weekend_user": "週末のみのユーザー",
        "report.glance": "ひと目でわかる",
        "report.glance_item": "<b>{n}人</b> — {label}",
        "report.insights_title": "で、何をすればいい?",
        "report.insights_note": "* 自動計算の参考値です。因果関係は実験で確認してください。",
        "report.index_title": "Dot Plot Reports",
        "report.index_body": "レポートは発行されたリンクからのみ閲覧できます。",
        "insight.aha": (
            "💡 <b>{name}</b>をしたユーザー{did}人のうち<b>{rate_did}</b>が常連になりました。"
            "していないユーザーは{rate_not}のみ。"
            "→ 登録直後にこの行動を促し、効果が本物か確認しましょう。"
        ),
        "insight.churn": (
            "⚠️ 全{total}人中<b>{churned}人({pct})</b>が初日以降戻ってきていません。"
            "→ 初日の体験(オンボーディング)を見直しましょう。"
        ),
        "insight.weekend": (
            "📅 <b>{n}人</b>は週末しか使いません。"
            "→ 平日の利用を妨げているものを、そのユーザーに直接聞いてみましょう。"
        ),
        "insight.none": "まだ明確なパターンはありません。データが貯まったら再確認してください。",
        "funnel.title": "新規ユーザーはどこで離脱する?",
        "funnel.signup": "登録",
        "funnel.first_value": "最初の価値体験",
        "funnel.returned": "別の日に再訪",
        "funnel.recent": "直近2週間で活動",
        "funnel.median_days": "登録 → 最初の価値までの日数(中央値): {days}日",
        "retention.title": "週次リテンション",
        "retention.subtitle": "登録後N週目に活動したユーザーの割合",
        "retention.week": "{n}週",
        "history.title": "前回レポート({date})比",
        "history.users": "ユーザー数",
        "history.regular_rate": "コアファン率",
        "history.churned_rate": "初日離脱率",
        "history.w1_retention": "1週目リテンション",
    },
}

DEFAULT_LANG = "en"


def t(lang: str, key: str, **kwargs) -> str:
    table = STRINGS.get(lang, STRINGS[DEFAULT_LANG])
    text = table.get(key) or STRINGS[DEFAULT_LANG][key]
    return text.format(**kwargs) if kwargs else text


def _placeholders(template: str) -> set[str]:
    import string

    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def register_custom(strings: dict[str, str]) -> list[str]:
    """에이전트가 번역한 문자열을 'custom' 언어로 등록한다.

    안전장치: 각 문장의 {자리표시자}가 영어 원본과 정확히 일치해야 한다.
    (번역하다가 {n}이나 {rate_did}를 빠뜨리면 숫자가 사라지므로)
    반환: 문제 있는 키 목록 (비어 있으면 성공, 문제 키는 영어로 대체됨)
    """
    en = STRINGS[DEFAULT_LANG]
    bad = []
    merged = dict(en)
    for key, value in strings.items():
        if key not in en:
            bad.append(f"{key} (알 수 없는 키)")
            continue
        if _placeholders(value) != _placeholders(en[key]):
            bad.append(f"{key} (자리표시자 불일치: {_placeholders(en[key])} 필요)")
            continue
        merged[key] = value
    STRINGS["custom"] = merged
    return bad
