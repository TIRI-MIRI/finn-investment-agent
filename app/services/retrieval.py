"""Primary source document retrieval service.

Enforces strict domain allowlists, SSRF protections, redirect validations,
streamed response size limits, and timeouts.
Permits only official company investor relations and exchange filing domains.
"""

from __future__ import annotations

import datetime
import ipaddress
import socket
import urllib.parse
from typing import Any, Dict, List, Optional, Set

import httpx

from app.core.models import DataSourceType, RetrievedDocument

# ── Centralized Primary-Source Allowlist ──────────────────────────────────
# Only official company IR websites for research companies and official exchanges.
# Broker research, news aggregators, blog sites, and social media are strictly prohibited.

ALLOWED_PRIMARY_DOMAINS: Dict[str, Set[str]] = {
    # Ticker -> Allowed root domains (all subdomains permitted)
    "RELIANCE": {"ril.com"},
    "HDFCBANK": {"hdfcbank.com", "hdfc.bank.in"},
    "INFY": {"infosys.com"},
    "TCS": {"tcs.com"},
    "TATAMOTORS": {"tatamotors.com"},
}

EXCHANGE_ALLOWED_DOMAINS: Set[str] = {
    "bseindia.com",
    "nseindia.com",
}

# Default configuration limits
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB maximum
DEFAULT_TIMEOUT_SECONDS = 10.0
MAX_REDIRECTS = 3

SUPPORTED_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "application/pdf",
}


class RetrievalSecurityError(Exception):
    """Raised when a URL violates domain allowlist or SSRF security checks."""


class RetrievalError(Exception):
    """Raised when an HTTP or network error occurs during retrieval."""


class PrimarySourceRetriever:
    """Retrieves primary documents with strict security and validation rules."""

    def __init__(
        self,
        allowed_domains: Optional[Dict[str, Set[str]]] = None,
        exchange_domains: Optional[Set[str]] = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: Optional[httpx.Client] = None,
    ):
        self.allowed_domains = allowed_domains or ALLOWED_PRIMARY_DOMAINS
        self.exchange_domains = exchange_domains or EXCHANGE_ALLOWED_DOMAINS
        self.max_bytes = max_bytes
        self.timeout = timeout
        self._client = client

    # ── URL & Hostname Validation ─────────────────────────────────────────

    def validate_url(self, url: str, ticker: Optional[str] = None) -> urllib.parse.ParseResult:
        """Validate URL scheme, credentials, and domain boundary against allowlists.

        Raises:
            RetrievalSecurityError if URL is invalid, unapproved, or has credentials.
        """
        if not url or not isinstance(url, str):
            raise RetrievalSecurityError("URL must be a non-empty string.")

        try:
            parsed = urllib.parse.urlparse(url.strip())
        except Exception as exc:
            raise RetrievalSecurityError(f"Malformed URL: {exc}") from exc

        # 1. Scheme check: HTTP or HTTPS only
        if parsed.scheme.lower() not in ("http", "https"):
            raise RetrievalSecurityError(
                f"Unsupported URL scheme '{parsed.scheme}'. Only http and https are permitted."
            )

        # 2. Credential rejection: no user:pass embedded in URL
        if parsed.username is not None or parsed.password is not None:
            raise RetrievalSecurityError(
                "URLs containing embedded user credentials are strictly prohibited."
            )

        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            raise RetrievalSecurityError("URL is missing a valid hostname.")

        # 3. SSRF Check on direct IP literals before hostname matching
        try:
            direct_ip = ipaddress.ip_address(hostname)
            if self._is_forbidden_ip(direct_ip):
                raise RetrievalSecurityError(
                    f"Direct access to private/loopback/reserved IP '{hostname}' is prohibited (SSRF defense)."
                )
            else:
                raise RetrievalSecurityError(
                    f"Direct IP access to '{hostname}' is not permitted; primary sources must use official domain names."
                )
        except ValueError:
            pass  # Not an IP literal, proceed to hostname allowlist matching

        # 4. Domain allowlist check
        if not self._is_hostname_allowed(hostname, ticker):
            raise RetrievalSecurityError(
                f"Host '{hostname}' is not in the approved primary-source allowlist."
            )

        # 5. SSRF Check: IP address resolution and validation for domain names
        self._validate_destination_ip(hostname, parsed.port)

        return parsed

    def _is_hostname_allowed(self, hostname: str, ticker: Optional[str] = None) -> bool:
        """Check if hostname matches or is a subdomain of an allowed root domain.

        Prevents lookalike domain attacks (e.g. 'ril.com.evil.com' is rejected).
        """
        candidate_roots: Set[str] = set(self.exchange_domains)
        if ticker:
            ticker_upper = ticker.upper()
            if ticker_upper in self.allowed_domains:
                candidate_roots.update(self.allowed_domains[ticker_upper])
        else:
            # Check all known primary domains if no specific ticker provided
            for domains in self.allowed_domains.values():
                candidate_roots.update(domains)

        for root in candidate_roots:
            root = root.lower().strip()
            # Exact match: "ril.com" == "ril.com"
            if hostname == root:
                return True
            # Subdomain match: "investors.ril.com".endswith(".ril.com")
            if hostname.endswith("." + root):
                return True

        return False

    def _validate_destination_ip(self, hostname: str, port: Optional[int] = None) -> None:
        """Resolve host and ensure IP is NOT loopback, private, link-local, or reserved."""
        # Check if the hostname itself is an IP literal
        try:
            direct_ip = ipaddress.ip_address(hostname)
            if self._is_forbidden_ip(direct_ip):
                raise RetrievalSecurityError(
                    f"Direct access to private/loopback/reserved IP '{hostname}' is prohibited (SSRF defense)."
                )
        except ValueError:
            pass  # Not an IP literal, proceed to DNS resolution

        # Resolve via DNS
        target_port = port or 443
        try:
            addr_info = socket.getaddrinfo(hostname, target_port, proto=socket.IPPROTO_TCP)
        except socket.gaierror as exc:
            # If DNS resolution fails, raise as retrieval error (e.g. offline testing)
            raise RetrievalError(f"DNS resolution failed for '{hostname}': {exc}") from exc

        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                if self._is_forbidden_ip(ip_obj):
                    raise RetrievalSecurityError(
                        f"Resolved IP '{ip_str}' for host '{hostname}' is in a forbidden range (SSRF defense)."
                    )
            except ValueError:
                continue

    @staticmethod
    def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Determine if an IP address is in a restricted range."""
        return (
            ip.is_loopback  # 127.0.0.0/8, ::1
            or ip.is_private  # 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
            or ip.is_link_local  # 169.254.0.0/16, fe80::/10
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified  # 0.0.0.0, ::
        )

    # ── Document Retrieval Pipeline ───────────────────────────────────────

    def retrieve_document(
        self,
        url: str,
        ticker: str,
        title: str,
        publisher: str,
        document_type: str = "annual_report",
        period: Optional[str] = None,
    ) -> RetrievedDocument:
        """Retrieve a primary source document with streaming size enforcement and manual redirect checks."""
        current_url = url
        retrieved_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Create or use client
        client = self._client or httpx.Client(
            timeout=httpx.Timeout(self.timeout),
            follow_redirects=False,  # Enforce manual redirect inspection
            headers={"User-Agent": "FINN-Research-Agent/1.0 (Primary Source Verification)"},
        )

        try:
            redirect_count = 0
            while redirect_count <= MAX_REDIRECTS:
                # 1. Validate URL & SSRF defense on current target
                self.validate_url(current_url, ticker=ticker)

                try:
                    response = client.get(current_url)
                except httpx.TimeoutException as exc:
                    return RetrievedDocument(
                        ticker=ticker,
                        title=title,
                        publisher=publisher,
                        url=url,
                        document_type=document_type,
                        period=period,
                        status="timeout",
                        error_message=f"Request timed out after {self.timeout}s: {exc}",
                        retrieved_at=retrieved_at,
                    )
                except httpx.RequestError as exc:
                    return RetrievedDocument(
                        ticker=ticker,
                        title=title,
                        publisher=publisher,
                        url=url,
                        document_type=document_type,
                        period=period,
                        status="failed",
                        error_message=f"HTTP transport error: {exc}",
                        retrieved_at=retrieved_at,
                    )

                # 2. Handle Redirects Manually
                if response.status_code in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        return RetrievedDocument(
                            ticker=ticker,
                            title=title,
                            publisher=publisher,
                            url=url,
                            document_type=document_type,
                            period=period,
                            status="failed",
                            error_message="Redirect response missing Location header.",
                            retrieved_at=retrieved_at,
                        )
                    # Resolve relative redirect targets safely
                    next_url = urllib.parse.urljoin(current_url, location)
                    current_url = next_url
                    redirect_count += 1
                    continue

                # 3. HTTP status code check
                if response.status_code != 200:
                    return RetrievedDocument(
                        ticker=ticker,
                        title=title,
                        publisher=publisher,
                        url=current_url,
                        document_type=document_type,
                        period=period,
                        status="failed",
                        error_message=f"HTTP {response.status_code}: {response.reason_phrase}",
                        retrieved_at=retrieved_at,
                    )

                # 4. Content-Type check
                raw_ct = response.headers.get("Content-Type", "").lower()
                clean_ct = raw_ct.split(";")[0].strip()
                if clean_ct not in SUPPORTED_CONTENT_TYPES:
                    return RetrievedDocument(
                        ticker=ticker,
                        title=title,
                        publisher=publisher,
                        url=current_url,
                        document_type=document_type,
                        period=period,
                        content_type=clean_ct or "unknown",
                        status="unsupported_type",
                        error_message=f"Unsupported Content-Type '{clean_ct}'. Allowed: {sorted(list(SUPPORTED_CONTENT_TYPES))}",
                        retrieved_at=retrieved_at,
                    )

                # 5. Bounded streaming read (enforce max_bytes)
                content_chunks: List[bytes] = []
                total_bytes = 0

                for chunk in response.iter_bytes(chunk_size=16384):
                    total_bytes += len(chunk)
                    if total_bytes > self.max_bytes:
                        return RetrievedDocument(
                            ticker=ticker,
                            title=title,
                            publisher=publisher,
                            url=current_url,
                            document_type=document_type,
                            period=period,
                            content_type=clean_ct,
                            status="oversized",
                            error_message=f"Response exceeded size limit of {self.max_bytes} bytes (streamed {total_bytes} bytes).",
                            retrieved_at=retrieved_at,
                        )
                    content_chunks.append(chunk)

                full_bytes = b"".join(content_chunks)

                return RetrievedDocument(
                    ticker=ticker,
                    title=title,
                    publisher=publisher,
                    url=current_url,
                    document_type=document_type,
                    period=period,
                    content_type=clean_ct,
                    status="success",
                    raw_bytes=full_bytes,
                    retrieved_at=retrieved_at,
                    is_primary=True,
                    is_fixture=False,
                )

            # Exceeded redirect hops
            return RetrievedDocument(
                ticker=ticker,
                title=title,
                publisher=publisher,
                url=url,
                document_type=document_type,
                period=period,
                status="failed",
                error_message=f"Exceeded maximum redirect limit of {MAX_REDIRECTS} hops.",
                retrieved_at=retrieved_at,
            )

        except RetrievalSecurityError as sec_err:
            return RetrievedDocument(
                ticker=ticker,
                title=title,
                publisher=publisher,
                url=url,
                document_type=document_type,
                period=period,
                status="failed",
                error_message=f"Security rejection: {sec_err}",
                retrieved_at=retrieved_at,
            )
        except Exception as exc:
            return RetrievedDocument(
                ticker=ticker,
                title=title,
                publisher=publisher,
                url=url,
                document_type=document_type,
                period=period,
                status="failed",
                error_message=f"Unexpected retrieval error: {exc}",
                retrieved_at=retrieved_at,
            )
        finally:
            if not self._client and client:
                client.close()
