from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TokenRecord:
    access_token: str
    generated_at: str
    trading_date: str
    api_key: str | None = None
    user_id: str | None = None

    def for_today(self, today: date | None = None) -> bool:
        expected = (today or date.today()).isoformat()
        return self.trading_date == expected and bool(self.access_token.strip())

    def safe_metadata(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "trading_date": self.trading_date,
            "api_key_present": bool(self.api_key),
            "user_id": self.user_id,
            "has_access_token": bool(self.access_token.strip()),
        }


class TokenStore:
    """Small file-backed store for the current Kite access token.

    The access token is intentionally kept outside .env. Callers must avoid logging
    the raw record returned by this store.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(
        self,
        *,
        access_token: str,
        api_key: str | None = None,
        user_id: str | None = None,
        generated_at: datetime | None = None,
        trading_date: date | None = None,
    ) -> TokenRecord:
        token = access_token.strip()
        if not token:
            raise ValueError("access_token cannot be empty")

        generated = generated_at or datetime.now()
        trade_date = trading_date or generated.date()
        record = TokenRecord(
            access_token=token,
            generated_at=generated.isoformat(),
            trading_date=trade_date.isoformat(),
            api_key=api_key,
            user_id=user_id,
        )
        self._write(record)
        return record

    def read(self) -> TokenRecord | None:
        if not self.path.exists():
            return None
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(data, dict):
            return None

        access_token = str(data.get("access_token") or "").strip()
        generated_at = str(data.get("generated_at") or "").strip()
        trading_date = str(data.get("trading_date") or "").strip()
        if not access_token or not generated_at or not trading_date:
            return None
        return TokenRecord(
            access_token=access_token,
            generated_at=generated_at,
            trading_date=trading_date,
            api_key=str(data["api_key"]).strip() if data.get("api_key") else None,
            user_id=str(data["user_id"]).strip() if data.get("user_id") else None,
        )

    def read_today(self, today: date | None = None) -> TokenRecord | None:
        record = self.read()
        if record is None or not record.for_today(today=today):
            return None
        return record

    def has_today_token(self, today: date | None = None) -> bool:
        return self.read_today(today=today) is not None

    def _write(self, record: TokenRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {
            "access_token": record.access_token,
            "generated_at": record.generated_at,
            "trading_date": record.trading_date,
            "api_key": record.api_key,
            "user_id": record.user_id,
        }
        tmp.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
