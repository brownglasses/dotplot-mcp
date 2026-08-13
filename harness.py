# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Harness: run the whole pipeline end-to-end without MCP.

Usage:
  uv run harness.py [lang]          plain run (lang: en/ko/ja, default en)
  uv run harness.py [lang] --slow   paced + colored, for recording the README GIF

--slow only changes presentation (pauses, color, a curated set of users so the
recording shows every pattern). The pipeline is identical either way — that's
the point of having one file instead of two.
"""
import re
import sys
import time

import analysis
import report as report_mod
from i18n import t

args = [a for a in sys.argv[1:] if not a.startswith("-")]
SLOW = "--slow" in sys.argv
LANG = args[0] if args else "en"
CSV = "events.csv"
VALUE_EVENT = "play_song"  # the event that means "user got real value"

TITLES = {
    "en": ["1. Describe the data", "2. Dot plot — one row per user, one cell per day",
           "3. Classify user patterns", "4. Aha moment — which action turns users into regulars?"],
    "ko": ["① 데이터 파악", "② 도트 플롯 — 유저 한 명이 한 줄, 하루가 한 칸",
           "③ 패턴 자동 분류", "④ 아하 모먼트 — 어떤 행동이 단골을 만드나?"],
    "ja": ["① データ把握", "② ドットプロット — 1人1行、1日1マス",
           "③ パターン自動分類", "④ アハ・モーメント — どの行動が常連を生むか?"],
}
titles = TITLES.get(LANG, TITLES["en"])

# 녹화용으로 고른 유저들 — 찐팬/주말러/이탈자/아하 전환 유저가 한 화면에 다 보이게
GIF_PICKS = ["user_001", "user_008", "user_017", "user_014",
             "user_030", "user_029", "user_028", "user_026"]

events = analysis.load_events(CSV)
users = analysis.build_users(events, VALUE_EVENT)
today = max(e["date"] for e in events)
start = min(e["date"] for e in events)


def bold(s: str) -> str:
    return f"\033[1m{s}\033[0m" if SLOW else s


def pause(sec: float) -> None:
    if SLOW:
        time.sleep(sec)


def section(title: str, after: float = 0) -> None:
    print()
    if SLOW:
        print(f"\033[1m━━ {title} " + "━" * max(58 - len(title), 0) + "\033[0m")
        time.sleep(1.2)
    else:
        print("=" * 68)
        print(title)
        print("=" * 68)
    pause(after)


if SLOW:
    print("\033[1;34m● Dot Plot MCP\033[0m — see individual users, not aggregate charts")
    time.sleep(1.5)

section(titles[0])
kinds: dict[str, int] = {}
for e in events:
    kinds[e["event"]] = kinds.get(e["event"], 0) + 1
print(f"users: {len(users)} / events: {len(events)} / {start} ~ {today}")
print(f"event types: {kinds}")
pause(2)

section(titles[1])
few = ({k: users[k] for k in GIF_PICKS if k in users} if SLOW
       else dict(sorted(users.items())[:12]))
marks = {"create_playlist": "P"} if SLOW else {"create_playlist": "P", "search": "S"}
print(analysis.render_dot_plot(few, start, 28, marks, lang=LANG))
pause(4)

section(titles[2])
buckets = analysis.classify_users(users, today)
for key, ids in buckets.items():
    print(f"  {len(ids):>2}  {t(LANG, f'bucket.{key}')}")
pause(3)

section(titles[3])
aha = analysis.find_aha_moments(events, users, VALUE_EVENT, today)
for r in aha:
    did_rate = bold(f"{r['did_regular_rate']:.0%}")
    lift = bold(f"{r['lift']:+.0%}")
    print(
        f"  {r['event']:<18} did: {r['did_count']:>2} -> regular {did_rate}"
        f" | didn't: {r['not_count']:>2} -> regular {r['not_regular_rate']:.0%}"
        f" | lift {lift}"
    )
pause(2.5)

# 마무리는 리포트가 쓰는 문장 그대로 — 데모용 문구를 따로 두면 또 두 벌이 된다.
# 그 문장들은 HTML용이라 <b>가 섞여 있으므로 터미널용으로 바꿔서 출력한다.
def for_terminal(s: str) -> str:
    if SLOW:
        return s.replace("<b>", "\033[1m").replace("</b>", "\033[0;32m")
    return re.sub(r"</?b>", "", s)


print()
for line in report_mod.build_insights(len(users), buckets, aha, lang=LANG):
    print(f"\033[0;32m→ {for_terminal(line)}\033[0m" if SLOW else f"-> {for_terminal(line)}")
pause(3.5)
