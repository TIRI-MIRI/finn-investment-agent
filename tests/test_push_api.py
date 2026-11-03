"""Integration tests for Push workflow API endpoints and UI window filtering."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Digest API Tests ─────────────────────────────────────────────────────


class TestDigestEndpoint:
    def test_digest_default_200(self):
        response = client.get("/api/digest")
        assert response.status_code == 200
        data = response.json()
        assert data["window"] == "24h"
        assert data["is_fixture"] is True
        assert "material_announcements" in data
        assert "routine_announcements" in data

    def test_digest_selectable_windows(self):
        for win in ("24h", "3d", "7d", "all"):
            response = client.get(f"/api/digest?window={win}")
            assert response.status_code == 200
            assert response.json()["window"] == win

    def test_digest_invalid_window_returns_422(self):
        response = client.get("/api/digest?window=invalid_window")
        assert response.status_code == 422
        assert "Invalid window" in response.json()["detail"]

    def test_digest_material_announcements_sorted_by_score(self):
        response = client.get("/api/digest?window=all")
        assert response.status_code == 200
        items = response.json()["material_announcements"]
        if len(items) >= 2:
            scores = [i["priority_score"] for i in items]
            assert scores == sorted(scores, reverse=True)


# ── Alerts API Tests ─────────────────────────────────────────────────────


class TestAlertsEndpoint:
    def test_alerts_default_200(self):
        response = client.get("/api/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "alerts" in data
        assert data["is_fixture"] is True

    def test_alerts_custom_thresholds(self):
        response = client.get("/api/alerts?price_threshold=2.0&volume_threshold=1.5")
        assert response.status_code == 200
        data = response.json()
        assert data["price_threshold_pct"] == 2.0
        assert data["volume_multiple_threshold"] == 1.5

    def test_alerts_contains_required_fields(self):
        response = client.get("/api/alerts?anomalies_only=false")
        assert response.status_code == 200
        alerts = response.json()["alerts"]
        assert len(alerts) > 0
        first = alerts[0]
        assert "ticker" in first
        assert "price_change_pct" in first
        assert "volume_ratio" in first
        assert "severity" in first
        assert "explanation" in first


# ── Results API Tests ────────────────────────────────────────────────────


class TestResultsEndpoints:
    def test_get_all_results_200(self):
        response = client.get("/api/results")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 3
        tickers = {r["ticker"] for r in data["results"]}
        assert "RELIANCE" in tickers
        assert "INFY" in tickers

    def test_get_ticker_results_reliance(self):
        response = client.get("/api/results/RELIANCE")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "RELIANCE"
        assert data["revenue"]["current"] == 243865.0
        assert data["unit"] == "₹ Cr"

    def test_get_ticker_results_not_found_returns_404(self):
        response = client.get("/api/results/NONEXISTENT")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ── UI Integration Tests (Today Screen with Push Workflow) ────────────────


class TestTodayPushUI:
    def test_today_renders_selectable_windows(self):
        response = client.get("/today?window=7d")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        html = response.text
        assert 'href="/today?window=24h"' in html
        assert 'href="/today?window=3d"' in html
        assert 'href="/today?window=7d"' in html
        assert 'href="/today?window=all"' in html
        assert 'class="window-btn active"' in html

    def test_today_renders_price_volume_anomalies(self):
        response = client.get("/today")
        assert response.status_code == 200
        html = response.text
        assert "Price &amp; Volume Anomalies" in html or "Price & Volume Anomalies" in html
        assert "TATAMOTORS" in html or "INFY" in html
        assert "threshold" in html.lower()

    def test_today_renders_quarterly_results_table(self):
        response = client.get("/today?window=all")
        assert response.status_code == 200
        html = response.text
        assert "Extracted Results" in html
        assert "Revenue" in html
        assert "EBITDA" in html
        assert "PAT (Net Profit)" in html

