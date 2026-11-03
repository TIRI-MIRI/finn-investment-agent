"""Validated, atomic JSON persistence for a single-process, single-user demo."""
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.models import AnnouncementCategory, CATEGORY_DEFAULT_PRIORITY, Priority


class MonitoringRules(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    price_threshold_pct: float = Field(3.0, ge=0.1, le=100)
    volume_multiple_threshold: float = Field(2.0, ge=0.5, le=50)
    trigger_mode: Literal["OR", "AND"] = "OR"
    monitored_tickers: list[str] | None = None
    event_types: list[AnnouncementCategory] = Field(default_factory=lambda: [
        c for c in AnnouncementCategory if CATEGORY_DEFAULT_PRIORITY.get(c) != Priority.LOW
    ])

    @field_validator("event_types")
    @classmethod
    def unique_events(cls, values):
        return list(dict.fromkeys(values))

    @field_validator("monitored_tickers")
    @classmethod
    def valid_tickers(cls, values):
        if values is None:
            return None
        from app.data.companies import PORTDATA
        allowed = {c.ticker for c in PORTDATA}
        if any(t not in allowed for t in values):
            raise ValueError('Select companies from the portfolio universe')
        return list(dict.fromkeys(values))


class MonitoringState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: MonitoringRules = Field(default_factory=MonitoringRules)
    acknowledged: dict[str, bool] = Field(default_factory=dict)


class MonitoringStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.lock = RLock()

    def load(self):
        with self.lock:
            try:
                return MonitoringState.model_validate_json(self.path.read_text(encoding="utf-8")), None
            except FileNotFoundError:
                return MonitoringState(), None
            except (ValueError, OSError):
                return MonitoringState(), "Saved monitoring preferences could not be read. Safe defaults are active; save to repair them."

    def _write(self, state):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        name = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as file:
                name = file.name
                file.write(state.model_dump_json(indent=2))
                file.flush()
                os.fsync(file.fileno())
            os.replace(name, self.path)
        finally:
            if name and os.path.exists(name):
                os.unlink(name)

    def save_rules(self, rules: MonitoringRules):
        with self.lock:
            state, _ = self.load()
            state.rules = rules
            self._write(state)
        return rules

    def acknowledge(self, alert_id: str, value: bool):
        with self.lock:
            state, warning = self.load()
            if warning:
                raise OSError("Repair monitoring preferences in Settings before acknowledging alerts.")
            if value:
                state.acknowledged[alert_id] = True
            else:
                state.acknowledged.pop(alert_id, None)
            self._write(state)
