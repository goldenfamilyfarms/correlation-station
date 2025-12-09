"""Tests for configuration settings"""
import pytest
import os
from app.config import Settings


class TestSettings:
    """Test Settings configuration"""

    def test_settings_defaults(self):
        """Settings should have sensible defaults"""
        settings = Settings()

        # App config
        assert settings.service_name == "correlation-engine"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"

        # Queue config
        assert settings.max_queue_size == 1000
        assert settings.queue_retry_attempts == 3
        assert settings.queue_retry_delay == 0.1

        # Correlation config
        assert settings.correlation_window_seconds == 60
        assert settings.max_correlation_age_hours == 24

    def test_settings_mdso_disabled_by_default(self):
        """MDSO should be disabled by default"""
        settings = Settings()

        assert settings.mdso_enabled is False

    def test_settings_mdso_config(self):
        """MDSO config should be None when disabled"""
        settings = Settings()

        # These should have defaults
        assert settings.mdso_base_url is None
        assert settings.mdso_username is None
        assert settings.mdso_password is None

    def test_settings_ssl_verification_enabled_default(self):
        """SSL verification should be enabled by default"""
        settings = Settings()

        assert settings.mdso_verify_ssl is True

    def test_settings_request_size_limits(self):
        """Request size limits should have defaults"""
        settings = Settings()

        assert settings.max_request_body_size == 10 * 1024 * 1024  # 10MB
        assert settings.max_protobuf_size == 10 * 1024 * 1024
        assert settings.max_json_size == 10 * 1024 * 1024

    def test_settings_otel_export_config(self):
        """OTEL export config should have defaults"""
        settings = Settings()

        assert settings.loki_url is not None
        assert settings.tempo_url is not None
        assert settings.otel_service_name == "correlation-engine"

    def test_settings_can_be_overridden_by_env(self, monkeypatch):
        """Settings should be overridable via environment variables"""
        monkeypatch.setenv("SERVICE_NAME", "custom-service")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("MAX_QUEUE_SIZE", "5000")

        settings = Settings()

        assert settings.service_name == "custom-service"
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.max_queue_size == 5000

    def test_settings_mdso_enabled_via_env(self, monkeypatch):
        """MDSO can be enabled via environment"""
        monkeypatch.setenv("MDSO_ENABLED", "true")
        monkeypatch.setenv("MDSO_BASE_URL", "https://mdso.example.com")
        monkeypatch.setenv("MDSO_USERNAME", "testuser")
        monkeypatch.setenv("MDSO_PASSWORD", "testpass")

        settings = Settings()

        assert settings.mdso_enabled is True
        assert settings.mdso_base_url == "https://mdso.example.com"
        assert settings.mdso_username == "testuser"

    def test_settings_ssl_verification_can_be_disabled(self, monkeypatch):
        """SSL verification can be disabled via environment"""
        monkeypatch.setenv("MDSO_VERIFY_SSL", "false")

        settings = Settings()

        assert settings.mdso_verify_ssl is False

    def test_settings_custom_ca_bundle(self, monkeypatch):
        """Custom CA bundle can be configured"""
        monkeypatch.setenv("MDSO_SSL_CA_BUNDLE", "/path/to/ca-bundle.crt")

        settings = Settings()

        assert settings.mdso_ssl_ca_bundle == "/path/to/ca-bundle.crt"

    def test_settings_queue_retry_config(self, monkeypatch):
        """Queue retry configuration can be customized"""
        monkeypatch.setenv("QUEUE_RETRY_ATTEMPTS", "5")
        monkeypatch.setenv("QUEUE_RETRY_DELAY", "0.5")

        settings = Settings()

        assert settings.queue_retry_attempts == 5
        assert settings.queue_retry_delay == 0.5

    def test_settings_correlation_window_config(self, monkeypatch):
        """Correlation window can be configured"""
        monkeypatch.setenv("CORRELATION_WINDOW_SECONDS", "120")
        monkeypatch.setenv("MAX_CORRELATION_AGE_HOURS", "48")

        settings = Settings()

        assert settings.correlation_window_seconds == 120
        assert settings.max_correlation_age_hours == 48

    def test_settings_request_size_limits_configurable(self, monkeypatch):
        """Request size limits can be configured"""
        monkeypatch.setenv("MAX_REQUEST_BODY_SIZE", str(50 * 1024 * 1024))  # 50MB
        monkeypatch.setenv("MAX_PROTOBUF_SIZE", str(20 * 1024 * 1024))  # 20MB

        settings = Settings()

        assert settings.max_request_body_size == 50 * 1024 * 1024
        assert settings.max_protobuf_size == 20 * 1024 * 1024

    def test_settings_token_expiry_config(self, monkeypatch):
        """Token expiry can be configured"""
        monkeypatch.setenv("MDSO_TOKEN_EXPIRY_SECONDS", "7200")

        settings = Settings()

        assert settings.mdso_token_expiry_seconds == 7200

    def test_settings_timeout_config(self, monkeypatch):
        """Timeout can be configured"""
        monkeypatch.setenv("MDSO_TIMEOUT", "60.0")

        settings = Settings()

        assert settings.mdso_timeout == 60.0

    def test_settings_basic_auth_config(self, monkeypatch):
        """Basic auth can be configured"""
        monkeypatch.setenv("BASIC_AUTH_USERNAME", "admin")
        monkeypatch.setenv("BASIC_AUTH_PASSWORD", "secret")

        settings = Settings()

        assert settings.basic_auth_username == "admin"
        assert settings.basic_auth_password == "secret"

    def test_settings_otel_export_enabled(self, monkeypatch):
        """OTEL export can be enabled/disabled"""
        monkeypatch.setenv("OTEL_EXPORT_ENABLED", "false")

        settings = Settings()

        assert settings.otel_export_enabled is False

    def test_settings_loki_tempo_urls(self, monkeypatch):
        """Loki and Tempo URLs can be configured"""
        monkeypatch.setenv("LOKI_URL", "http://loki.example.com:3100")
        monkeypatch.setenv("TEMPO_URL", "http://tempo.example.com:4317")

        settings = Settings()

        assert settings.loki_url == "http://loki.example.com:3100"
        assert settings.tempo_url == "http://tempo.example.com:4317"

    def test_settings_prometheus_config(self, monkeypatch):
        """Prometheus metrics can be configured"""
        monkeypatch.setenv("METRICS_PORT", "9090")

        settings = Settings()

        assert settings.metrics_port == 9090


class TestSettingsValidation:
    """Test Settings validation logic"""

    def test_settings_positive_queue_size(self):
        """Queue size must be positive"""
        settings = Settings(max_queue_size=1000)
        assert settings.max_queue_size > 0

    def test_settings_positive_retry_attempts(self):
        """Retry attempts must be positive"""
        settings = Settings(queue_retry_attempts=3)
        assert settings.queue_retry_attempts > 0

    def test_settings_positive_correlation_window(self):
        """Correlation window must be positive"""
        settings = Settings(correlation_window_seconds=60)
        assert settings.correlation_window_seconds > 0

    def test_settings_reasonable_max_age(self):
        """Max correlation age should be reasonable"""
        settings = Settings(max_correlation_age_hours=24)
        assert settings.max_correlation_age_hours >= 1


class TestSettingsEnvironmentModes:
    """Test different environment configurations"""

    def test_settings_development_mode(self, monkeypatch):
        """Development mode should have appropriate defaults"""
        monkeypatch.setenv("ENVIRONMENT", "development")

        settings = Settings()

        assert settings.environment == "development"

    def test_settings_production_mode(self, monkeypatch):
        """Production mode configuration"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "WARNING")

        settings = Settings()

        assert settings.environment == "production"
        assert settings.log_level == "WARNING"

    def test_settings_staging_mode(self, monkeypatch):
        """Staging mode configuration"""
        monkeypatch.setenv("ENVIRONMENT", "staging")

        settings = Settings()

        assert settings.environment == "staging"
