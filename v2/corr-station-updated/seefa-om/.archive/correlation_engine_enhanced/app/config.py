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

    # Export retry settings
    export_retry_attempts: int = 3
    export_retry_delay: float = 1.0
    export_timeout: float = 10.0
    enable_circuit_breaker: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60

    # Backend URLs
    loki_url: str = "http://loki:3100/loki/api/v1/push"
    tempo_grpc_endpoint: str = "tempo:4317"
    tempo_http_endpoint: str = "http://tempo:4318"
    prometheus_pushgateway: Optional[str] = None

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
    
    # NEW: MDSO settings
    mdso_enabled: bool = False
    mdso_url: Optional[str] = None
    mdso_user: Optional[str] = None
    mdso_pass: Optional[str] = None
    mdso_collection_interval: int = 3600  # 1 hour
    mdso_time_range_hours: int = 3

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
