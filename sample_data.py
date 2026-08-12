# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""가짜 이벤트 데이터 생성기.

실제 서비스라면 DB에 쌓여 있을 이벤트 로그를 흉내낸다.
음악 앱이라고 가정: play_song(핵심 가치), search, create_playlist, open_app(허영 지표)

유저 유형을 일부러 섞어둔다 — 인스타 글에 나온 패턴 그대로:
  - daily:    데이브처럼 거의 매일 쓰는 유저
  - weekend:  주말에만 쓰는 유저
  - churned:  가입날 한 번 쓰고 사라진 유저 (온보딩 문제)
  - aha:      띄엄띄엄 쓰다가 create_playlist 이후 매일 쓰게 된 유저
"""
import csv
import random
from datetime import date, timedelta

random.seed(42)  # 매번 같은 데이터가 나오게 고정

START = date(2026, 7, 1)
DAYS = 42  # 6주

USER_TYPES = [
    ("daily", 6),
    ("weekend", 7),
    ("churned", 12),   # 초기 앱은 이탈이 제일 많다
    ("aha", 8),
    ("casual", 7),     # 불규칙하게 가끔 쓰는 유저
]


def days_active(kind: str, signup_offset: int) -> tuple[list[int], int | None]:
    """유저 유형별로 '활동한 날'의 목록과 (있다면) 아하 이벤트가 발생한 날을 돌려준다."""
    days = []
    aha_day = None
    for d in range(signup_offset, DAYS):
        weekday = (START + timedelta(days=d)).weekday()  # 5,6 = 주말
        if kind == "daily":
            if random.random() < 0.85:
                days.append(d)
        elif kind == "weekend":
            if weekday >= 5 and random.random() < 0.9:
                days.append(d)
        elif kind == "churned":
            if d == signup_offset:
                days.append(d)
        elif kind == "aha":
            if aha_day is None:
                # 가입 후 3~10일 사이 어느 날 플레이리스트를 만든다
                if d == signup_offset or random.random() < 0.25:
                    days.append(d)
                    if d >= signup_offset + 3 and random.random() < 0.5:
                        aha_day = d
            else:
                if random.random() < 0.9:  # 아하 이후엔 거의 매일
                    days.append(d)
        elif kind == "casual":
            if random.random() < 0.2:
                days.append(d)
    return days, aha_day


def main() -> None:
    rows = []
    uid = 0
    for kind, count in USER_TYPES:
        for _ in range(count):
            uid += 1
            user = f"user_{uid:03d}"
            platform = random.choice(["ios", "android"])
            signup_offset = random.randint(0, DAYS - 14)
            active, aha_day = days_active(kind, signup_offset)
            for d in active:
                day = START + timedelta(days=d)
                # 하루 안에서 벌어지는 이벤트들
                rows.append([user, platform, day.isoformat(), "open_app"])
                rows.append([user, platform, day.isoformat(), "play_song"])
                if random.random() < 0.3:
                    rows.append([user, platform, day.isoformat(), "search"])
                if aha_day == d:
                    rows.append([user, platform, day.isoformat(), "create_playlist"])

    rows.sort(key=lambda r: (r[2], r[0]))
    with open("events.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "platform", "date", "event"])
        w.writerows(rows)
    print(f"events.csv 생성 완료: 유저 {uid}명, 이벤트 {len(rows)}건")


if __name__ == "__main__":
    main()
