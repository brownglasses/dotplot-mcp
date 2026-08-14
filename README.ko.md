# Dot Plot MCP

> DAU/MAU 말고, 유저 한 명 한 명을 보세요.

[English](README.md) | **한국어**

![report](.github/report_ko.png)

## 설치

이 한 줄을 에이전트에게 붙여넣으면 알아서 다 설치합니다:

```
Dotplot (MCP + 스킬) 설치해줘 — 안내는 여기에 있어 https://dotplot-reports.vercel.app/setup.md
```

<details>
<summary>직접 하려면</summary>

```bash
claude mcp add --scope user dotplot -- uvx dotplot-mcp
```

</details>

## 사용

아무 프로젝트에서나 이렇게 말하면 됩니다:

> **"우리 서비스 분석해줘"**

위 리포트가 나옵니다. 그게 전부예요.

슬래시 명령어로도 됩니다:

```
/dotplot-analyze-product    전체 분석 + 리포트
/dotplot-add-tracking       빠진 로깅 찾아서 심어주기
/dotplot-whats-changed      지난번 리포트 대비 변화
```

Claude가 알아서 데이터를 찾고, "이 행동을 했으면 가치를 얻은 것"에 해당하는
이벤트를 고르고, 리포트를 만듭니다. **events 테이블 없어도 됩니다** —
`orders` 테이블이 이미 이벤트 로그거든요:

```sql
SELECT user_id, created_at::date AS date, 'purchase' AS event FROM orders
UNION ALL
SELECT user_id, added_at::date, 'add_to_wishlist' FROM wishlist_items
```

추적을 아직 안 하고 있다면 **"추적 안 되고 있는 거 심어줘"** 라고 하세요.
Claude가 코드를 읽고, 빠진 로깅을 짜 넣고, 며칠 뒤에 다시 오면 되는지 알려줍니다.

<details>
<summary>아직 분석할 서비스가 없다면 샘플로 체험</summary>

```bash
git clone https://github.com/brownglasses/dotplot-mcp && cd dotplot-mcp
uv run sample_data.py   # 패턴을 심어둔 가짜 유저 40명 생성
uv run harness.py       # 전체 파이프라인을 눈으로 확인
```

</details>

## 왜 만들었나

DAU/MAU 그래프는 신규 유저가 들어오는 한 "우상향"합니다 — 아무도 남지 않아도요.
유저가 수백 명이 되기 전까지 창업자에게 가장 유용한 대시보드는
[YC의 도트 플롯](https://www.youtube.com/watch?v=e5-6rEwzxLs)(David Lieb)입니다.
**유저 한 명 = 한 줄, 하루 = 한 칸.**

숫자가 거짓말하지 않도록 네 가지 규칙을 지킵니다:

- **계산은 코드, 해석만 AI** — 같은 데이터면 언제나 같은 숫자
- **표본이 작으면 판단 보류** — 5명 미만 그룹에 대해서는 아무 말도 안 함
- **상관 ≠ 인과** — 모든 발견에 "믿기 전에 실험으로 확인하라" 경고 동봉
- **허영 지표 거부** — `open_app`을 핵심 가치로 고르면 코드가 거절

리포트는 사용자의 언어로 나옵니다 (영어·한국어·일본어 내장, 그 외 언어는
즉석 번역하되 숫자가 그대로인지 코드가 검증).

## 더 보기

- [툴별 설명과 익명 벤치마크](docs/tools.md)
- [어떻게 만들었나](docs/architecture.md)

MIT
