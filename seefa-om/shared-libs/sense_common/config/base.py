"""Base configuration classes using Pydantic Settings"""
from typing import Literal, Optional
from pydantic import Field, AnyHttpUrl, SecretStr
from pydantic_settings import BaseSettings


class MDSOConfig(BaseSettings):
    """MDSO connection configuration"""

    mdso_base_url: AnyHttpUrl = Field(..., description="MDSO base URL")
    mdso_username: str = Field(..., description="MDSO username")
    mdso_password: SecretStr = Field(..., description="MDSO password")
    mdso_verify_ssl: bool = Field(default=True, description="Verify SSL certificates")
    mdso_ssl_ca_bundle: Optional[str] = Field(default=None, description="Custom CA bundle path")
    mdso_timeout: float = Field(default=30.0, ge=1, le=300, description="Request timeout in seconds")
    mdso_token_expiry_seconds: int = Field(default=3600, ge=300, description="Token expiry duration")

    class Config:
        env_prefix = "MDSO_"
        env_file = ".env"
        case_sensitive = False


class OTELConfig(BaseSettings):
    """OpenTelemetry configuration"""

    otel_endpoint: AnyHttpUrl = Field(
        default="http://gateway:4318",
        description="OTEL collector endpoint"
    )
    otel_protocol: Literal["grpc", "http"] = Field(
        default="http",
        description="OTEL protocol (grpc or http)"
    )
    otel_enabled: bool = Field(
        default=True,
        description="Enable OTEL instrumentation"
    )
    otel_service_name: str = Field(..., description="Service name for telemetry")
    otel_service_version: str = Field(default="1.0.0", description="Service version")

    class Config:
        env_prefix = "OTEL_"
        env_file = ".env"
        case_sensitive = False


class BaseServiceConfig(BaseSettings):
    """
    Base configuration for all Sense services

    All Sense applications (Palantir, Arda, Beorn) should inherit from this
    to ensure consistent configuration management.

    Example:
        class PalantirConfig(BaseServiceConfig):
            service_name: str = "palantir"
            # Add Palantir-specific config here
    """

    # Service identity
    service_name: str = Field(..., description="Service name (palantir, arda, beorn)")
    service_version: str = Field(default="1.0.0", description="Service version")
    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev",
        description="Deployment environment"
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    workers: int = Field(default=4, ge=1, le=32, description="Number of worker processes")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log format"
    )

    # HTTP Client
    http_timeout: float = Field(default=30.0, ge=1, le=300, description="HTTP request timeout")
    http_max_retries: int = Field(default=3, ge=0, le=10, description="HTTP retry attempts")
    http_verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    # CORS
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )

    # Health checks
    health_check_interval: int = Field(
        default=30,
        ge=5,
        description="Health check interval in seconds"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def get_mdso_config(self) -> MDSOConfig:
        """Get MDSO configuration"""
        return MDSOConfig()

    def get_otel_config(self, service_name: Optional[str] = None) -> OTELConfig:
        """Get OTEL configuration"""
        return OTELConfig(otel_service_name=service_name or self.service_name)
