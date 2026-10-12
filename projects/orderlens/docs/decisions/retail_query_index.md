# 공개 거래 기간 집계와 복합 인덱스

작성: 2026-10-12 · 버전: 0.6.0

## 문제와 조회 조건

541,907개의 공개 거래 행에서 특정 국가의 비취소 거래를 기간으로 집계하면 인덱스가 없을 때 모든 행을 읽습니다. 비교할 SQL의 의미를 먼저 고정했습니다.

- 국가 이름은 정확히 일치
- `is_cancellation = false`
- 원천에 시간대가 없으므로 timezone 없는 지역 시각 사용
- 시작 시각은 포함하고 종료 시각은 제외
- 결과는 행 수, 수량 합, 부호 있는 GBP 행 금액 합

`orderlens/retail_analytics.py`가 이 조건을 한 쿼리로 만들고, 빈 결과는 0으로 반환합니다. 금액은 회계상 매출이 아니라 정제된 `quantity × unit_price`의 합입니다.

## 선택한 인덱스

세 번째 Alembic 리비전 `20261012_03`에서 다음 인덱스를 추가했습니다.

```text
(country, is_cancellation, invoice_at_local)
```

국가와 취소 여부는 동등 조건이고 거래 시각은 범위 조건입니다. 동등 조건을 먼저 두고 범위 컬럼을 뒤에 두어 한 국가의 비취소 기간만 탐색하도록 했습니다. `line_amount`와 `quantity`까지 넣는 covering index는 읽기 비용을 더 줄일 수 있지만, 현재 고정 조회 하나를 위해 인덱스를 더 크게 만들지 않았습니다. 쓰기 비용과 다른 국가·기간의 선택도는 후속 측정 대상입니다.

## 측정 방법과 결과

Linux x86_64, Python 3.12.14, SQLite 3.53.1에서 전체 UCI 정제 행 541,907개를 사용했습니다. 같은 인덱스 적용 DB에서 SQLite의 `NOT INDEXED`와 `INDEXED BY`로 계획만 고정했습니다. 각 쿼리를 5회 예열한 뒤 실행 순서를 번갈아 31회씩 측정했습니다. 비교 대상은 Germany, `[2011-01-01, 2012-01-01)`입니다.

| 항목 | 강제 전체 스캔 | 강제 복합 인덱스 |
|---|---:|---:|
| 실행계획 | `SCAN retail_lines` | `SEARCH ... ix_retail_country_cancelled_time` |
| 중앙값 | 41.062 ms | 1.917 ms |
| p95 | 46.255 ms | 2.731 ms |
| 최소~최대 | 37.913~46.268 ms | 1.610~3.274 ms |

두 계획 모두 8,529행, 수량 112,385, 부호 있는 금액 GBP 213,626.000000으로 같았습니다. 중앙값 비율은 21.42배였지만, 이는 한 컴퓨터의 warm-cache SQLite·한 조건에서 얻은 비교입니다. 운영 환경이나 PostgreSQL의 성능 향상으로 일반화하지 않습니다.

인덱스가 사용한 공간은 SQLite `dbstat` 기준 27,430,912바이트였습니다. DB 파일은 140,288,000바이트에서 167,718,912바이트로 늘어 기존 파일 대비 19.55%의 저장 공간을 추가로 사용했습니다. 원본 결과는 [retail_query_benchmark.json](../../artifacts/retail_query_benchmark.json)에 있습니다.

```bash
ORDERLENS_DATABASE_URL=sqlite:///retail.db python -m alembic upgrade head
python -m scripts.benchmark_retail_sql \
  --database-url sqlite:///retail.db \
  --country Germany \
  --start 2011-01-01T00:00:00 \
  --end 2012-01-01T00:00:00 \
  --warmups 5 --runs 31
```

PostgreSQL 16.15 통합 검사는 10만 합성 행 중 Germany 1,000행을 같은 조건으로 집계했습니다. `ANALYZE` 뒤 기본 planner는 이 인덱스의 `Index Scan`을 선택했고, 인덱스 계열 scan을 끈 계획은 `Seq Scan`이었습니다. [원격 실행](https://github.com/Ajsjee3/Ajsjee3/actions/runs/38237841801)의 한 번의 시간은 성능 주장으로 사용하지 않습니다.

## 참고와 남은 범위

[eugene-khyst/postgresql-performance-essentials](https://github.com/eugene-khyst/postgresql-performance-essentials/tree/8a9eaddaeee2917ddd72587f4cad6044d6d2b566)의 실행계획·복합 인덱스 예제를 읽었습니다. `EXPLAIN ANALYZE`로 실제 계획을 보고, 동등 조건 뒤에 범위 조건을 두며, 인덱스의 저장·쓰기 비용도 함께 본다는 기준만 적용했습니다. 예제 코드와 PostgreSQL 13 설정은 가져오지 않았습니다.

전체 UCI 자료를 PostgreSQL에 적재한 비교, cold-cache 반복, 동시 쓰기 지연, 여러 국가·기간에 대한 선택도는 확인하지 않았습니다. 작은 학습 과제는 인덱스를 `(invoice_at_local, country, is_cancellation)` 순서로 바꾸면 Germany 조회에서 왜 더 넓은 범위를 읽을 수 있는지 설명하는 것입니다.
