# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""하네스: MCP 없이 계산 로직만 처음부터 끝까지 돌려보는 시험대.

순서가 곧 실제 사용 흐름이다:
  ① 데이터 파악 → ② 도트 플롯 → ③ 패턴 분류 → ④ 아하 모먼트 탐색
"""
from datetime import date

import analysis

CSV = "events.csv"
VALUE_EVENT = "play_song"  # 핵심 가치 = 노래를 실제로 들었다

events = analysis.load_events(CSV)
users = analysis.build_users(events, VALUE_EVENT)
today = max(e["date"] for e in events)
start = min(e["date"] for e in events)

print("=" * 70)
print("① 데이터 파악")
print("=" * 70)
kinds: dict[str, int] = {}
for e in events:
    kinds[e["event"]] = kinds.get(e["event"], 0) + 1
print(f"유저 {len(users)}명 / 이벤트 {len(events)}건 / {start} ~ {today}")
print(f"이벤트 종류: {kinds}")

print()
print("=" * 70)
print("② 도트 플롯 (처음 12명만)")
print("=" * 70)
few = dict(sorted(users.items())[:12])
print(analysis.render_dot_plot(few, start, 28, {"create_playlist": "P", "search": "S"}))

print()
print("=" * 70)
print("③ 패턴 자동 분류")
print("=" * 70)
for name, ids in analysis.classify_users(users, today).items():
    print(f"  {name}: {len(ids)}명")

print()
print("=" * 70)
print("④ 아하 모먼트 자동 탐색")
print("=" * 70)
for r in analysis.find_aha_moments(events, users, VALUE_EVENT, today):
    print(
        f"  {r['event']:<18} 한 사람 {r['did_count']:>2}명 중 단골률 {r['did_regular_rate']:.0%}"
        f" / 안 한 사람 {r['not_count']:>2}명 중 {r['not_regular_rate']:.0%}"
        f"  → 차이 {r['lift']:+.0%}"
    )
print()
print("검증 성공 조건: create_playlist의 차이(lift)가 search보다 커야 한다.")
print("(샘플 데이터를 그렇게 심어놨기 때문 — 도구가 심어둔 정답을 찾아내는지 시험)")
