from datetime import timezone
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

OrderSource = Literal["market_a", "market_b", "own_store"]


class OrderInput(BaseModel):
    """한 주문의 한 버전입니다. 배송 상태가 바뀌면 revision을 올립니다."""

    model_config = ConfigDict(extra="forbid")
    source: OrderSource
    order_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    revision: Annotated[StrictInt, Field(ge=1, le=2_147_483_647)]
    placed_at: AwareDatetime
    updated_at: AwareDatetime
    promised_by: AwareDatetime
    delivered_at: AwareDatetime | None = None
    status: Literal["paid", "shipped", "delivered", "cancelled", "refunded"]
    amount_krw: Annotated[StrictInt, Field(ge=0, le=1_000_000_000_000)]

    @field_validator("placed_at", "updated_at", "promised_by", "delivered_at", mode="before")
    @classmethod
    def reject_numeric_timestamp(cls, value):
        if isinstance(value, (int, float, bool)):
            raise ValueError("날짜는 시간대가 포함된 ISO 8601 문자열이어야 합니다.")
        return value

    @field_validator("placed_at", "updated_at", "promised_by", "delivered_at")
    @classmethod
    def normalize_utc(cls, value):
        return value.astimezone(timezone.utc) if value is not None else None

    @model_validator(mode="after")
    def check_times(self) -> Self:
        if self.updated_at < self.placed_at:
            raise ValueError("updated_at은 placed_at보다 빠를 수 없습니다.")
        if self.promised_by < self.placed_at:
            raise ValueError("promised_by는 placed_at보다 빠를 수 없습니다.")
        if self.status == "delivered" and self.delivered_at is None:
            raise ValueError("배송 완료 주문은 delivered_at이 필요합니다.")
        if self.delivered_at is not None:
            if self.status not in {"delivered", "refunded"}:
                raise ValueError("delivered_at은 배송 완료 또는 환불 주문에만 허용합니다.")
            if not self.placed_at <= self.delivered_at <= self.updated_at:
                raise ValueError("배송 시각은 주문 시각과 갱신 시각 사이여야 합니다.")
        return self


class IngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # 개별 행을 여기서 검증하지 않아 잘못된 행만 별도로 기록할 수 있습니다.
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=500)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=200)
    top_k: int = Field(default=3, ge=1, le=5)

    @field_validator("query")
    @classmethod
    def strip_query(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("검색어를 두 글자 이상 입력해 주세요.")
        return value
