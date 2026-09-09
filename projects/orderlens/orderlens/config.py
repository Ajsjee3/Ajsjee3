import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./orderlens.db"
    api_key: str = "orderlens-local-demo-key"

    @classmethod
    def from_env(cls) -> "Settings":
        key = os.getenv("ORDERLENS_API_KEY", "orderlens-local-demo-key")
        if len(key) < 16:
            raise ValueError("ORDERLENS_API_KEY는 16자 이상이어야 합니다.")
        return cls(
            database_url=os.getenv("ORDERLENS_DATABASE_URL", "sqlite:///./orderlens.db"),
            api_key=key,
        )
