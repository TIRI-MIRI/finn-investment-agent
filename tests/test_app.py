"""Tests for the FastAPI application — health check and basic endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_ok(self):
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_contains_mode(self):
        data = client.get("/health").json()
        assert data["mode"] in ("demo", "live")

    def test_health_contains_version(self):
        data = client.get("/health").json()
        assert "version" in data


class TestPortfolioEndpoint:
    def test_portfolio_returns_200(self):
        response = client.get("/api/portfolio")
        assert response.status_code == 200

    def test_portfolio_count(self):
        data = client.get("/api/portfolio").json()
        assert 15 <= data["count"] <= 20

    def test_portfolio_is_fixture(self):
        data = client.get("/api/portfolio").json()
        assert data["is_fixture"] is True

    def test_portfolio_has_companies(self):
        data = client.get("/api/portfolio").json()
        assert len(data["companies"]) == data["count"]
        for c in data["companies"]:
            assert "ticker" in c
            assert "name" in c


class TestAnnouncementsEndpoint:
    def test_announcements_returns_200(self):
        response = client.get("/api/announcements")
        assert response.status_code == 200

    def test_announcements_count(self):
        data = client.get("/api/announcements").json()
        assert data["count"] >= 8

    def test_announcements_is_fixture(self):
        data = client.get("/api/announcements").json()
        assert data["is_fixture"] is True

