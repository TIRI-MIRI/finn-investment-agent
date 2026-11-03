"""Unit tests for PrimarySourceRetriever: domain allowlists, SSRF protection, and stream limits."""

from unittest.mock import MagicMock, patch
import urllib.parse

import httpx
import pytest

from app.services.retrieval import (
    DEFAULT_MAX_BYTES,
    PrimarySourceRetriever,
    RetrievalError,
    RetrievalSecurityError,
)


@pytest.fixture
def retriever():
    return PrimarySourceRetriever(max_bytes=1024 * 100, timeout=2.0)  # 100 KB for test


# ── Domain Allowlist & Host Validation ───────────────────────────────────


class TestDomainAllowlist:
    def test_approved_company_domains(self, retriever):
        assert retriever._is_hostname_allowed("ril.com", ticker="RELIANCE")
        assert retriever._is_hostname_allowed("www.ril.com", ticker="RELIANCE")
        assert retriever._is_hostname_allowed("investors.ril.com", ticker="RELIANCE")
        assert retriever._is_hostname_allowed("infosys.com", ticker="INFY")
        assert retriever._is_hostname_allowed("www.hdfcbank.com", ticker="HDFCBANK")
        assert retriever._is_hostname_allowed("tcs.com", ticker="TCS")
        assert retriever._is_hostname_allowed("tatamotors.com", ticker="TATAMOTORS")

    def test_approved_exchange_domains(self, retriever):
        assert retriever._is_hostname_allowed("bseindia.com")
        assert retriever._is_hostname_allowed("www.bseindia.com")
        assert retriever._is_hostname_allowed("nseindia.com")
        assert retriever._is_hostname_allowed("www.nseindia.com")

    def test_rejected_lookalike_domains(self, retriever):
        """Prevent suffix/lookalike domain attacks."""
        assert not retriever._is_hostname_allowed("ril.com.attacker.com", ticker="RELIANCE")
        assert not retriever._is_hostname_allowed("fake-ril.com", ticker="RELIANCE")
        assert not retriever._is_hostname_allowed("notinfosys.com", ticker="INFY")
        assert not retriever._is_hostname_allowed("nseindia.com.phishing.org")
        assert not retriever._is_hostname_allowed("bseindia.com.evil.com")

    def test_unapproved_general_domains(self, retriever):
        """Disallow news aggregators, broker research, and social media."""
        assert not retriever._is_hostname_allowed("moneycontrol.com")
        assert not retriever._is_hostname_allowed("economictimes.indiatimes.com")
        assert not retriever._is_hostname_allowed("bloomberg.com")
        assert not retriever._is_hostname_allowed("reuters.com")
        assert not retriever._is_hostname_allowed("google.com")


# ── SSRF & URL Scheme Protections ────────────────────────────────────────


class TestSSRFProtections:
    def test_reject_non_http_schemes(self, retriever):
        with pytest.raises(RetrievalSecurityError, match="Unsupported URL scheme"):
            retriever.validate_url("ftp://ril.com/report.pdf", ticker="RELIANCE")

        with pytest.raises(RetrievalSecurityError, match="Unsupported URL scheme"):
            retriever.validate_url("file:///etc/passwd", ticker="RELIANCE")

        with pytest.raises(RetrievalSecurityError, match="Unsupported URL scheme"):
            retriever.validate_url("gopher://ril.com/", ticker="RELIANCE")

    def test_reject_embedded_credentials(self, retriever):
        with pytest.raises(RetrievalSecurityError, match="embedded user credentials"):
            retriever.validate_url("https://admin:password@ril.com/secret", ticker="RELIANCE")

    def test_reject_loopback_and_private_ips(self, retriever):
        with pytest.raises(RetrievalSecurityError, match="SSRF defense"):
            retriever.validate_url("http://127.0.0.1/admin")

        with pytest.raises(RetrievalSecurityError, match="SSRF defense"):
            retriever.validate_url("http://10.0.0.1/internal")

        with pytest.raises(RetrievalSecurityError, match="SSRF defense"):
            retriever.validate_url("http://192.168.1.1/router")

        with pytest.raises(RetrievalSecurityError, match="SSRF defense"):
            retriever.validate_url("http://169.254.169.254/latest/meta-data/")  # AWS metadata

    def test_reject_dns_resolving_to_private_ip(self, retriever):
        """Simulate DNS rebinding or internal resolution to 127.0.0.1."""
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            with pytest.raises(RetrievalSecurityError, match="forbidden range"):
                retriever.validate_url("https://ril.com/report.html", ticker="RELIANCE")


# ── Mocked Retrieval Execution ───────────────────────────────────────────


class TestMockedRetrieval:
    @patch.object(PrimarySourceRetriever, "validate_url", return_value=None)
    def test_successful_html_retrieval(self, mock_val):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        mock_resp.iter_bytes.return_value = [b"<html><body><h1>Q3 Report</h1><p>Revenue up</p></body></html>"]

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        retriever = PrimarySourceRetriever(client=mock_client)
        doc = retriever.retrieve_document(
            url="https://investors.ril.com/q3.html",
            ticker="RELIANCE",
            title="RIL Q3 Report",
            publisher="Reliance Industries Limited",
        )

        assert doc.status == "success"
        assert doc.content_type == "text/html"
        assert b"Q3 Report" in doc.raw_bytes
        assert doc.is_fixture is False
        assert doc.is_primary is True

    @patch.object(PrimarySourceRetriever, "validate_url", return_value=None)
    def test_successful_pdf_retrieval(self, mock_val):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/pdf"}
        mock_resp.iter_bytes.return_value = [b"%PDF-1.4 test binary bytes"]

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        retriever = PrimarySourceRetriever(client=mock_client)
        doc = retriever.retrieve_document(
            url="https://www.infosys.com/investors/report.pdf",
            ticker="INFY",
            title="Infosys Annual Report",
            publisher="Infosys Limited",
        )

        assert doc.status == "success"
        assert doc.content_type == "application/pdf"
        assert doc.raw_bytes == b"%PDF-1.4 test binary bytes"

    @patch.object(PrimarySourceRetriever, "validate_url", return_value=None)
    def test_timeout_handling(self, mock_val):
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Read timed out")

        retriever = PrimarySourceRetriever(client=mock_client)
        doc = retriever.retrieve_document(
            url="https://ril.com/slow",
            ticker="RELIANCE",
            title="Slow Doc",
            publisher="RIL",
        )

        assert doc.status == "timeout"
        assert "timed out" in doc.error_message.lower()

    @patch.object(PrimarySourceRetriever, "validate_url", return_value=None)
    def test_http_404_error(self, mock_val):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.reason_phrase = "Not Found"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        retriever = PrimarySourceRetriever(client=mock_client)
        doc = retriever.retrieve_document(
            url="https://ril.com/missing.pdf",
            ticker="RELIANCE",
            title="Missing",
            publisher="RIL",
        )

        assert doc.status == "failed"
        assert "HTTP 404" in doc.error_message

    @patch.object(PrimarySourceRetriever, "validate_url", return_value=None)
    def test_unsupported_content_type(self, mock_val):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "application/x-msdownload"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        retriever = PrimarySourceRetriever(client=mock_client)
        doc = retriever.retrieve_document(
            url="https://ril.com/malicious.exe",
            ticker="RELIANCE",
            title="Exe File",
            publisher="RIL",
        )

        assert doc.status == "unsupported_type"
        assert "Unsupported Content-Type" in doc.error_message

    @patch.object(PrimarySourceRetriever, "validate_url", return_value=None)
    def test_oversized_response_stream_limit(self, mock_val):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"Content-Type": "text/html"}
        # Return 64KB chunks totaling > 100KB limit
        mock_resp.iter_bytes.return_value = [b"A" * 65536, b"B" * 65536]

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        retriever = PrimarySourceRetriever(max_bytes=100000, client=mock_client)  # 100KB limit
        doc = retriever.retrieve_document(
            url="https://ril.com/large.html",
            ticker="RELIANCE",
            title="Large",
            publisher="RIL",
        )

        assert doc.status == "oversized"
        assert "exceeded size limit" in doc.error_message.lower()

    def test_redirect_to_unapproved_host_rejected(self):
        """Ensure redirects to unapproved external domains are caught and rejected."""
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.headers = {"Location": "https://evil-unapproved.com/steal-data"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        with patch.object(PrimarySourceRetriever, "validate_url") as mock_val:
            # First call succeeds on initial URL, second call raises security error on redirect target
            mock_val.side_effect = [None, RetrievalSecurityError("Host 'evil-unapproved.com' is not approved")]

            retriever = PrimarySourceRetriever(client=mock_client)
            doc = retriever.retrieve_document(
                url="https://investors.ril.com/redirect",
                ticker="RELIANCE",
                title="Redirect test",
                publisher="RIL",
            )

            assert doc.status == "failed"
            assert "Security rejection" in doc.error_message

