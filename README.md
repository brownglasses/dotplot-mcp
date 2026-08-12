# Dot Plot MCP

> DAU/MAU 말고, 유저 한 명 한 명을 보세요.
> *See individual users, not aggregate charts — YC's Dot Plot methodology as an MCP server.*

YC 파트너 David Lieb의 [Dot Plot 방법론](https://www.youtube.com/watch?v=e5-6rEwzxLs)을
MCP 서버로 만들었습니다. 유저가 수백 명이 되기 전까지, 창업자에게 필요한 건
거창한 대시보드가 아니라 **유저 한 명 = 한 줄, 하루 = 한 칸**인 표 하나입니다.

**설계 원칙: 숫자는 코드가 계산하고, AI는 해석만 합니다.** 그래서 통계가 틀리지 않습니다.

## 뭘 해주나

```
① 추적 점검   코드에 심은 이벤트 vs 실제 찍힌 데이터 대조 → 고장·구멍 발견
② 도트 플롯   유저별 활동을 점으로 — 이탈, 주말러, 찐팬이 한눈에
③ 패턴 분류   한번쓰고떠남 / 주말에만 / 거의매일 자동 분류
④ 아하 탐색   모든 행동을 훑어서 "단골로 바꾸는 행동" 후보 발견
⑤ 리포트     손그림 스타일 HTML + 쉬운 말 인사이트 → 링크로 공유
⑥ 벤치마크   (옵트인) 같은 업종·단계 팀들과 내 지표 비교
```

## 시작하기

필요한 것: [uv](https://docs.astral.sh/uv/), 그리고 `user_id, date, event` 3칸짜리 CSV.

```bash
# Claude Code에 등록
claude mcp add dotplot -- uv run --python 3.12 /path/to/dotplot-mcp/server.py

# 데이터가 아직 없다면 샘플로 체험
uv run sample_data.py   # events.csv 생성 (가짜 유저 40명)
uv run harness.py       # 전체 파이프라인을 눈으로 확인
```

그다음 Claude에게:

> "events.csv 분석해서 아하 모먼트 찾아줘"

내 DB에서 뽑으려면 이 정도면 됩니다:

```sql
SELECT user_id, created_at::date AS date, 'purchase' AS event FROM orders;
```

## 툴 목록

| 툴 | 하는 일 |
|---|---|
| `describe_events` | 데이터 구조 파악 (항상 먼저 호출) |
| `dot_plot` | 텍스트 도트 플롯 (◎ 가입일, ● 활동, 커스텀 마크) |
| `classify_users` | 행동 패턴별 자동 분류 |
| `find_aha_moments` | 전 이벤트 대상 "단골 전환 행동" 자동 탐색 |
| `audit_tracking` | 코드 속 이벤트 vs 데이터 대조 (추적 구멍 발견) |
| `generate_report` | YC 손그림 스타일 HTML 리포트 + 규칙 기반 인사이트 |
| `publish_report` | 리포트를 무작위 주소로 호스팅, 공유 링크 발급 (Vercel) |
| `submit_benchmark` | 익명 벤치마크에 집계값 제출 (명시적 동의 필수) |
| `compare_benchmark` | 같은 업종·단계 팀들의 백분위와 내 지표 비교 |

## 익명 벤치마크 — 뭐가 전송되나

**옵트인입니다.** 동의 없이는 아무것도 전송되지 않습니다.

동의하면 전송되는 것 — 아래 집계값 5개가 **전부**입니다:

```json
{
  "users_count": 40,
  "churned_rate": 0.30,
  "weekend_rate": 0.175,
  "regular_rate": 0.275,
  "aha_lift": 0.82
}
```

전송되지 **않는** 것: 유저 ID, 이벤트 로그, 날짜, 서비스 이름, IP 기반 식별자.

백엔드는 INSERT 전용(RLS)이라 제출된 데이터를 익명 키로 다시 읽을 방법이 없고,
비교 조회는 백분위 통계만 반환하는 함수를 통해서만 가능합니다.
직접 확인: [benchmark.py](benchmark.py) (60줄).

## 구조

```
analysis.py    모든 계산 — MCP를 모르는 순수 파이썬 (여기가 두뇌)
server.py      계산을 MCP 툴로 노출하는 얇은 껍데기
report.py      HTML 리포트 렌더링 + 규칙 기반 인사이트 문장
benchmark.py   익명 벤치마크 클라이언트
harness.py     Claude 없이 전체 흐름을 돌려보는 시험대
sample_data.py 정답을 심어둔 샘플 데이터 (도구 검증용)
hosting/       리포트 호스팅용 Vercel 프로젝트 템플릿
```

## 왜 이렇게 만들었나

- **LLM은 계산하지 않는다** — 같은 데이터면 언제나 같은 숫자
- **표본이 작으면 판단 보류** — 5명 미만 그룹은 아하 후보에서 제외
- **상관 ≠ 인과** — 모든 인사이트에 "실험으로 검증하라" 경고 내장
- **허영 지표 차단** — `open_app` 같은 이벤트를 고르면 다시 고르라고 안내

## License

MIT
