"""Tests for MDSO Client - SSL verification and token expiry"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import httpx

from app.mdso.client import MDSOClient


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient"""
    with patch('app.mdso.client.httpx.AsyncClient') as mock:
        client = AsyncMock()
        mock.return_value = client
        yield client


class TestSSLVerification:
    """Test SSL verification configuration"""

    def test_ssl_enabled_by_default(self, mock_httpx_client):
        """SSL verification should be enabled by default"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test"
        )

        # Verify SSL is enabled (verify=True)
        mock_httpx_client.assert_called_once()
        call_kwargs = mock_httpx_client.call_args[1]
        assert call_kwargs['verify'] is True

    def test_ssl_can_be_disabled(self, mock_httpx_client):
        """SSL verification can be disabled for dev"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test",
            verify_ssl=False
        )

        # Verify SSL is disabled
        call_kwargs = mock_httpx_client.call_args[1]
        assert call_kwargs['verify'] is False

    def test_custom_ca_bundle(self, mock_httpx_client):
        """Custom CA bundle can be provided"""
        ca_bundle = "/path/to/ca-bundle.crt"
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test",
            ssl_ca_bundle=ca_bundle
        )

        # Verify CA bundle is used
        call_kwargs = mock_httpx_client.call_args[1]
        assert call_kwargs['verify'] == ca_bundle

    def test_warning_logged_when_ssl_disabled(self, mock_httpx_client, caplog):
        """Warning should be logged when SSL verification is disabled"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test",
            verify_ssl=False
        )

        # Check warning was logged
        assert "SSL verification disabled" in caplog.text


class TestTokenExpiry:
    """Test token expiry and renewal"""

    @pytest.mark.asyncio
    async def test_token_cached_when_not_expired(self, mock_httpx_client):
        """Token should be reused if not expired"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test"
        )

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-token-123"}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        # First call - should fetch token
        token1 = await client.get_token()
        assert token1 == "test-token-123"
        assert mock_httpx_client.post.call_count == 1

        # Second call - should reuse cached token
        token2 = await client.get_token()
        assert token2 == "test-token-123"
        assert mock_httpx_client.post.call_count == 1  # Still only 1 call

    @pytest.mark.asyncio
    async def test_token_renewed_when_expired(self, mock_httpx_client):
        """Token should be renewed if expired"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test",
            token_expiry_seconds=1  # 1 second expiry for testing
        )

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-token-123"}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        # First call - should fetch token
        token1 = await client.get_token()
        assert token1 == "test-token-123"

        # Manually expire the token
        client._token_expiry = datetime.now(timezone.utc) - timedelta(seconds=10)

        # Second call - should fetch new token
        mock_response.json.return_value = {"token": "test-token-456"}
        token2 = await client.get_token()
        assert token2 == "test-token-456"
        assert mock_httpx_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_token_expiry_set_correctly(self, mock_httpx_client):
        """Token expiry should be set to current time + expiry_seconds"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test",
            token_expiry_seconds=3600  # 1 hour
        )

        # Set up mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "test-token-123"}
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        before = datetime.now(timezone.utc)
        await client.get_token()
        after = datetime.now(timezone.utc)

        # Verify expiry is set correctly (within 1 hour +/- 5 seconds)
        expected_expiry = before + timedelta(seconds=3600)
        assert client._token_expiry is not None
        assert abs((client._token_expiry - expected_expiry).total_seconds()) < 5

    @pytest.mark.asyncio
    async def test_token_expiry_cleared_on_delete(self, mock_httpx_client):
        """Token expiry should be cleared when token is deleted"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test"
        )

        # Set up token
        client._token = "test-token"
        client._token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        # Mock delete response
        mock_httpx_client.delete = AsyncMock()

        # Delete token
        await client.delete_token()

        # Verify token and expiry are cleared
        assert client._token is None
        assert client._token_expiry is None


class TestConfigurableTimeout:
    """Test configurable timeout"""

    def test_default_timeout(self, mock_httpx_client):
        """Default timeout should be 30 seconds"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test"
        )

        call_kwargs = mock_httpx_client.call_args[1]
        assert call_kwargs['timeout'] == 30.0

    def test_custom_timeout(self, mock_httpx_client):
        """Custom timeout can be set"""
        client = MDSOClient(
            base_url="https://mdso.example.com",
            username="test",
            password="test",
            timeout=60.0
        )

        call_kwargs = mock_httpx_client.call_args[1]
        assert call_kwargs['timeout'] == 60.0
