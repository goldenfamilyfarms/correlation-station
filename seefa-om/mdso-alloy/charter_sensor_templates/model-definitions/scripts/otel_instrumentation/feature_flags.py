"""Feature flags for OTel instrumentation"""
import os

def is_otel_enabled() -> bool:
    """Check if OTel instrumentation is enabled"""
    return os.getenv("OTEL_ENABLED", "true").lower() == "true"

def is_otel_sampling_enabled() -> bool:
    """Check if OTel sampling is enabled (for high-volume operations)"""
    return os.getenv("OTEL_SAMPLING_ENABLED", "true").lower() == "true"

def get_otel_sampling_rate() -> float:
    """Get OTel sampling rate (0.0 to 1.0)"""
    return float(os.getenv("OTEL_SAMPLING_RATE", "1.0"))

