"""Async HTTP client with retry and circuit breaker"""
import asyncio
import time
from typing import Optional, Any, Dict
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
import structlog

logger = structlog.get_logger()


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0


class CircuitBreaker:
    """Circuit breaker pattern implementation"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = timedelta(seconds=recovery_timeout)
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        self.name = name

    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == "closed":
            return True

        if self.state == "open":
            # Check if recovery timeout elapsed
            if self.last_failure_time and datetime.now() - self.last_failure_time >= self.recovery_timeout:
                self.state = "half-open"
                logger.info(f"Circuit breaker {self.name} half-open, testing connection")
                return True
            return False

        # half-open state - allow single request
        return True

    def record_success(self):
        """Record successful execution"""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info(f"Circuit breaker {self.name} closed, connection recovered")

    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state != "open":
                self.state = "open"
                logger.warning(
                    f"Circuit breaker {self.name} open, too many failures",
                    failures=self.failure_count,
                    recovery_timeout=self.recovery_timeout.total_seconds()
                )


class AsyncHTTPClient:
    """
    Async HTTP client with retry logic and circuit breaker

    Features:
    - Automatic retries with exponential backoff
    - Circuit breaker to prevent cascading failures
    - Configurable SSL verification
    - Structured logging
    - Timeout handling

    Example:
        client = AsyncHTTPClient(
            base_url="https://api.example.com",
            timeout=30.0,
            verify_ssl=True
        )

        response = await client.get("/endpoint", retry=True)
        data = response.json()

        await client.close()
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        verify_ssl: bool = True,
        ssl_ca_bundle: Optional[str] = None,
        retry_config: Optional[RetryConfig] = None,
        enable_circuit_breaker: bool = True,
        circuit_breaker_config: Optional[Dict[str, Any]] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.retry_config = retry_config or RetryConfig()

        # Configure SSL
        verify = verify_ssl
        if ssl_ca_bundle:
            verify = ssl_ca_bundle

        # Create HTTP client
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify,
            follow_redirects=True
        )

        # Circuit breaker
        self.circuit_breaker: Optional[CircuitBreaker] = None
        if enable_circuit_breaker:
            cb_config = circuit_breaker_config or {}
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=cb_config.get("failure_threshold", 5),
                recovery_timeout=cb_config.get("recovery_timeout", 60),
                name=cb_config.get("name", base_url)
            )

        if not verify_ssl:
            logger.warning(
                "HTTP client SSL verification disabled",
                base_url=base_url,
                recommendation="Set verify_ssl=True in production"
            )

    async def request(
        self,
        method: str,
        path: str,
        *,
        retry: bool = True,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry and circuit breaker

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: Request path (will be appended to base_url)
            retry: Whether to retry on failure
            **kwargs: Additional arguments passed to httpx

        Returns:
            httpx.Response object

        Raises:
            httpx.HTTPError: On HTTP errors after retries exhausted
        """
        url = f"{self.base_url}{path}"

        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            raise RuntimeError(f"Circuit breaker open for {self.base_url}")

        if not retry:
            return await self._make_request(method, url, **kwargs)

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.retry_config.max_attempts):
            try:
                response = await self._make_request(method, url, **kwargs)

                # Record success for circuit breaker
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()

                return response

            except httpx.HTTPError as e:
                last_exception = e

                # Don't retry on client errors (4xx)
                if hasattr(e, 'response') and 400 <= e.response.status_code < 500:
                    raise

                # Record failure for circuit breaker
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()

                # Calculate backoff delay
                if attempt < self.retry_config.max_attempts - 1:
                    delay = min(
                        self.retry_config.initial_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )

                    logger.warning(
                        f"Request failed, retrying in {delay}s",
                        method=method,
                        url=url,
                        attempt=attempt + 1,
                        max_attempts=self.retry_config.max_attempts,
                        error=str(e)
                    )

                    await asyncio.sleep(delay)

        # All retries exhausted
        logger.error(
            "Request failed after all retries",
            method=method,
            url=url,
            attempts=self.retry_config.max_attempts
        )
        raise last_exception

    async def _make_request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request"""
        response = await self._client.request(method, url, **kwargs)
        response.raise_for_status()
        return response

    async def get(self, path: str, *, retry: bool = True, **kwargs) -> httpx.Response:
        """Make GET request"""
        return await self.request("GET", path, retry=retry, **kwargs)

    async def post(self, path: str, *, retry: bool = True, **kwargs) -> httpx.Response:
        """Make POST request"""
        return await self.request("POST", path, retry=retry, **kwargs)

    async def put(self, path: str, *, retry: bool = True, **kwargs) -> httpx.Response:
        """Make PUT request"""
        return await self.request("PUT", path, retry=retry, **kwargs)

    async def delete(self, path: str, *, retry: bool = True, **kwargs) -> httpx.Response:
        """Make DELETE request"""
        return await self.request("DELETE", path, retry=retry, **kwargs)

    async def patch(self, path: str, *, retry: bool = True, **kwargs) -> httpx.Response:
        """Make PATCH request"""
        return await self.request("PATCH", path, retry=retry, **kwargs)

    async def close(self):
        """Close HTTP client"""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
