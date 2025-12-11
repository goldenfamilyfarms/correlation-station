"""
Demo configuration for Correlation Engine
Blueprint Feature 7: Public Demo Branch

When DEMO_MODE=true, adjust configuration for demo deployment
"""
import os

# Feature flag for demo mode
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() == "true"

# Database configuration
if DEMO_MODE:
    DATABASE_PATH = "demo_correlation_station.db"
    REDIS_HOST = os.getenv("REDIS_HOST", "redis-demo")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = 0
    REDIS_PASSWORD = None  # No password for demo

    # Observability endpoints (demo)
    LOKI_URL = os.getenv("LOKI_URL", "http://loki-demo:3100")
    TEMPO_GRPC_ENDPOINT = os.getenv("TEMPO_GRPC_ENDPOINT", "tempo-demo:4317")
    PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus-demo:9090")

    # API configuration
    API_RATE_LIMIT = "100/minute"  # Lower rate limit for demo
    API_CORS_ORIGINS = ["*"]  # Allow all origins for demo

    # Feature flags
    ENABLE_AUTH = False  # Disable auth for demo
    ENABLE_TELEMETRY = True
    ENABLE_SECA_AUTOMATION = True
    ENABLE_LEARNING_PORTAL = True

    print("🎭 DEMO MODE ENABLED: Using demo configuration")
else:
    DATABASE_PATH = os.getenv("DATABASE_PATH", "correlation_station.db")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = 0
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

    # Observability endpoints (production)
    LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
    TEMPO_GRPC_ENDPOINT = os.getenv("TEMPO_GRPC_ENDPOINT", "tempo:4317")
    PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")

    # API configuration
    API_RATE_LIMIT = os.getenv("API_RATE_LIMIT", "1000/minute")
    API_CORS_ORIGINS = os.getenv("API_CORS_ORIGINS", "").split(",") if os.getenv("API_CORS_ORIGINS") else []

    # Feature flags
    ENABLE_AUTH = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    ENABLE_TELEMETRY = os.getenv("ENABLE_TELEMETRY", "true").lower() == "true"
    ENABLE_SECA_AUTOMATION = os.getenv("ENABLE_SECA_AUTOMATION", "true").lower() == "true"
    ENABLE_LEARNING_PORTAL = os.getenv("ENABLE_LEARNING_PORTAL", "true").lower() == "true"

    print("✓ Production mode: Using production configuration")


def is_demo_mode() -> bool:
    """Check if running in demo mode"""
    return DEMO_MODE


def get_database_path() -> str:
    """Get database file path"""
    return DATABASE_PATH


def get_redis_config() -> dict:
    """Get Redis connection configuration"""
    return {
        "host": REDIS_HOST,
        "port": REDIS_PORT,
        "db": REDIS_DB,
        "password": REDIS_PASSWORD
    }


def get_observability_config() -> dict:
    """Get observability endpoints configuration"""
    return {
        "loki_url": LOKI_URL,
        "tempo_grpc_endpoint": TEMPO_GRPC_ENDPOINT,
        "prometheus_url": PROMETHEUS_URL
    }


def get_feature_flags() -> dict:
    """Get feature flags"""
    return {
        "enable_auth": ENABLE_AUTH,
        "enable_telemetry": ENABLE_TELEMETRY,
        "enable_seca_automation": ENABLE_SECA_AUTOMATION,
        "enable_learning_portal": ENABLE_LEARNING_PORTAL
    }
