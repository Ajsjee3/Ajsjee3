"""실제 개인정보가 없는 합성 주문을 생성합니다. 생성 결과는 항상 같습니다."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

AS_OF = "2026-09-08T00:00:00Z"


def generate_rows():
    rows = []
    base = datetime(2026, 9, 1, tzinfo=timezone.utc)
    for i in range(120):
        placed = base + timedelta(hours=i % 48)
        stage = i % 6
        row = {
            "source": ["market_a", "market_b", "own_store"][(i // 6) % 3],
            "order_id": f"DEMO-{i:04d}",
            "revision": 1,
            "placed_at": placed.isoformat(),
            "updated_at": placed.isoformat(),
            "promised_by": (placed + timedelta(hours=48)).isoformat(),
            "delivered_at": None,
            "status": "paid",
            "amount_krw": (i % 11 + 1) * 1000,
        }
        rows.append(row.copy())
        if stage in {1, 2, 3, 5}:
            row = {
                **row,
                "revision": 2,
                "status": "shipped",
                "updated_at": (placed + timedelta(hours=12)).isoformat(),
            }
            rows.append(row.copy())
        if stage in {2, 3, 5}:
            delivered = placed + timedelta(hours=72 if stage == 3 else 24)
            row = {
                **row,
                "revision": 3,
                "status": "delivered",
                "updated_at": delivered.isoformat(),
                "delivered_at": delivered.isoformat(),
            }
            rows.append(row.copy())
        if stage == 4:
            rows.append(
                {
                    **row,
                    "revision": 2,
                    "status": "cancelled",
                    "updated_at": (placed + timedelta(hours=6)).isoformat(),
                }
            )
        if stage == 5:
            rows.append(
                {
                    **row,
                    "revision": 4,
                    "status": "refunded",
                    "updated_at": (delivered + timedelta(hours=1)).isoformat(),
                }
            )
    rows.extend(row.copy() for row in rows[:5])
    rows.extend(
        [
            {**rows[0], "order_id": "BAD-MONEY", "amount_krw": -100},
            {**rows[0], "order_id": "BAD-DATE", "placed_at": "not-a-date"},
            {**rows[0], "order_id": "BAD-TIMEZONE", "updated_at": "2026-09-01T00:00:00"},
            {**rows[0], "amount_krw": 999999},
        ]
    )
    return rows


def main():
    destination = Path("data/demo_batch.json")
    destination.parent.mkdir(exist_ok=True)
    payload = {"rows": generate_rows()}
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"합성 데이터 {len(payload['rows'])}행: {destination}")


if __name__ == "__main__":
    main()
