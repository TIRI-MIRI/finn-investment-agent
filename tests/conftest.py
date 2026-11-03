"""Keep all tests independent of the local user's saved monitoring preferences."""
import pytest
import main
from app.services.monitoring_store import MonitoringStore


@pytest.fixture(autouse=True)
def isolated_monitoring_store(tmp_path, monkeypatch):
    store = MonitoringStore(tmp_path / "monitoring.json")
    monkeypatch.setattr(main, "monitoring_store", store)
    return store
