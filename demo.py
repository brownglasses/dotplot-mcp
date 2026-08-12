# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Paced demo for the README GIF — same pipeline as harness.py, with pauses.

Run: uv run demo.py
"""
import time
from datetime import date

import analysis
from i18n import t

CSV = "events.csv"
VALUE_EVENT = "play_song"
LANG = "en"

events = analysis.load_events(CSV)
users = analysis.build_users(events, VALUE_EVENT)
today = max(e["date"] for e in events)
start = min(e["date"] for e in events)


def section(title: str, pause: float = 1.2) -> None:
    print()
    print(f"\033[1m━━ {title} " + "━" * (58 - len(title)) + "\033[0m")
    time.sleep(pause)


print("\033[1;34m● Dot Plot MCP\033[0m — see individual users, not aggregate charts")
time.sleep(1.5)

section("1. Your event log (any 3-column CSV)")
print("   user_id, date, event")
print(f"   {len(users)} users / {len(events)} events / {start} ~ {today}")
time.sleep(2)

section("2. Dot plot — one row per user, one cell per day")
# 데모용 유저 셀렉션: 찐팬 / 주말러 / 이탈자 / P(아하 전환) 유저가 다 보이게
picks = ["user_001", "user_008", "user_017", "user_014", "user_030", "user_029", "user_028", "user_026"]
few = {k: users[k] for k in picks if k in users}
print(analysis.render_dot_plot(few, start, 28, {"create_playlist": "P"}, lang=LANG))
time.sleep(4)

section("3. Patterns, classified automatically")
for key, ids in analysis.classify_users(users, today).items():
    print(f"   {len(ids):>2}  {t(LANG, f'bucket.{key}')}")
time.sleep(3)

section("4. Aha moment — which action turns users into regulars?")
for r in analysis.find_aha_moments(events, users, VALUE_EVENT, today):
    print(
        f"   {r['event']:<17} did it -> \033[1m{r['did_regular_rate']:.0%}\033[0m regulars"
        f"   didn't -> {r['not_regular_rate']:.0%}   lift \033[1m{r['lift']:+.0%}\033[0m"
    )
time.sleep(2.5)
print()
print("\033[1;32m→ create_playlist turns users into daily users. Test it in onboarding.\033[0m")
time.sleep(3.5)
