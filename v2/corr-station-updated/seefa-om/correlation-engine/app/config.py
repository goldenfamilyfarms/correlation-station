"""Configuration settings for Correlation Engine"""
from typing import List, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Server settings
    port: int = 8080
    log_level: str = "info"

    # Correlation settings
    corr_window_seconds: int = 60
    max_batch_size: int = 5000
    max_queue_size: int = 10000
    max_correlation_history: int = 10000

    # Advanced correlation features
    enable_trace_synthesis: bool = True
    correlation_confidence_threshold: float = 0.5
    trace_synthesis_window_seconds: int = 60

    # Backend URLs
    loki_url: str = "http://loki:3100/loki/api/v1/push"
    tempo_grpc_endpoint: str = "tempo:4317"
    tempo_http_endpoint: str = "http://tempo:4318"
    prometheus_pushgateway: Optional[str] = None

    # Export retry settings
    export_retry_attempts: int = 3
    export_retry_delay: float = 1.0
    export_timeout: float = 10.0
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    # Authentication
    enable_basic_auth: bool = False
    basic_auth_user: Optional[str] = None
    basic_auth_pass: Optional[str] = None

    # CORS
    allow_origins: List[str] = ["*"]

    # Datadog (optional dual-write)
    datadog_api_key: Optional[str] = None
    datadog_site: str = "datadoghq.com"

    # Deployment
    deployment_env: str = "dev"

    # Self-Observability (correlation engine monitoring itself)
    enable_self_observability: bool = True
    self_observability_datadog_enabled: bool = False
    self_observability_metric_interval_ms: int = 60000

    # Pyroscope Profiling
    enable_pyroscope: bool = True
    pyroscope_server_address: str = "http://pyroscope:4040"
    pyroscope_application_name: str = "correlation-engine"
    pyroscope_sample_rate: int = 100  # Hz (samples per second)
    pyroscope_detect_subprocesses: bool = True
    pyroscope_log_level: str = "info"

    # MDSO Client Settings
    mdso_base_url: Optional[str] = None
    mdso_username: Optional[str] = None
    mdso_password: Optional[str] = None
    mdso_verify_ssl: bool = True
    mdso_ssl_ca_bundle: Optional[str] = None
    mdso_timeout: float = 30.0
    mdso_token_expiry_seconds: int = 3600  # 1 hour

    # HTTP Client Settings
    http_verify_ssl: bool = True
    http_max_connections: int = 100
    http_max_keepalive_connections: int = 20

    # Queue Settings
    queue_retry_attempts: int = 3
    queue_retry_delay: float = 0.1
    enable_queue_metrics: bool = True

    # Request Size Limits (security)
    max_request_body_size: int = 10 * 1024 * 1024  # 10MB
    max_protobuf_size: int = 10 * 1024 * 1024  # 10MB
    max_json_size: int = 10 * 1024 * 1024  # 10MB

    # State Management & Horizontal Scaling
    use_redis_state: bool = False  # Feature flag for Redis state management
    redis_url: str = "redis://localhost:6379"  # Redis connection URL
    redis_max_connections: int = 50  # Max connections in pool
    redis_key_prefix: str = "corr:"  # Prefix for all Redis keys
    correlation_ttl_seconds: int = 3600  # TTL for correlations (1 hour)
    correlation_window_seconds: int = 60  # Time window for correlation
    max_correlation_age_hours: int = 24  # Max age before cleanup

    @field_validator('allow_origins', mode='before')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            if not v or v.strip() == '':
                return ["*"]
            return [x.strip() for x in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
