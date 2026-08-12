# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Harness: run the whole pipeline end-to-end without MCP.

Usage: uv run harness.py [lang]   (lang: en/ko/ja, default en)
The order mirrors real usage:
  1. describe data -> 2. dot plot -> 3. classify patterns -> 4. find aha moments
"""
import sys
from datetime import date

import analysis
from i18n import t

LANG = sys.argv[1] if len(sys.argv) > 1 else "en"
CSV = "events.csv"
VALUE_EVENT = "play_song"  # the event that means "user got real value"

TITLES = {
    "en": ["1. Describe the data", "2. Dot plot (first 12 users)",
           "3. Classify user patterns", "4. Find aha moments"],
    "ko": ["① 데이터 파악", "② 도트 플롯 (처음 12명)", "③ 패턴 자동 분류", "④ 아하 모먼트 자동 탐색"],
    "ja": ["① データ把握", "② ドットプロット (最初の12人)", "③ パターン自動分類", "④ アハ・モーメント探索"],
}
titles = TITLES.get(LANG, TITLES["en"])

events = analysis.load_events(CSV)
users = analysis.build_users(events, VALUE_EVENT)
today = max(e["date"] for e in events)
start = min(e["date"] for e in events)


def section(title: str) -> None:
    print()
    print("=" * 68)
    print(title)
    print("=" * 68)


section(titles[0])
kinds: dict[str, int] = {}
for e in events:
    kinds[e["event"]] = kinds.get(e["event"], 0) + 1
print(f"users: {len(users)} / events: {len(events)} / {start} ~ {today}")
print(f"event types: {kinds}")

section(titles[1])
few = dict(sorted(users.items())[:12])
print(analysis.render_dot_plot(few, start, 28, {"create_playlist": "P", "search": "S"}, lang=LANG))

section(titles[2])
for key, ids in analysis.classify_users(users, today).items():
    print(f"  {t(LANG, f'bucket.{key}')}: {len(ids)}")

section(titles[3])
for r in analysis.find_aha_moments(events, users, VALUE_EVENT, today):
    print(
        f"  {r['event']:<18} did: {r['did_count']:>2} -> regular {r['did_regular_rate']:.0%}"
        f" | didn't: {r['not_count']:>2} -> regular {r['not_regular_rate']:.0%}"
        f" | lift {r['lift']:+.0%}"
    )
