"""Feature flags for OTel instrumentation"""
import os

def _get_config_value(key: str, default_value, instance=None):
    """
    Get configuration value from CommonPlan constant or environment variable.
    
    Priority:
    1. CommonPlan class constant (if instance is provided and has the attribute)
    2. Environment variable
    3. Default value
    """
    # Try to get from instance/class constants first
    if instance is not None:
        # Check if instance has the constant
        if hasattr(instance, key):
            value = getattr(instance, key)
            if value is not None:
                return value
        # Also check the class
        if hasattr(instance.__class__, key):
            value = getattr(instance.__class__, key)
            if value is not None:
                return value
    
    # Fall back to environment variable
    return os.getenv(key, default_value)

def is_otel_enabled(instance=None) -> bool:
    """
    Check if OTel instrumentation is enabled.
    
    Args:
        instance: Optional CommonPlan instance to get constants from
    
    Returns:
        True if OTel is enabled, False otherwise
    """
    value = _get_config_value("OTEL_ENABLED", "true", instance)
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"

def is_otel_sampling_enabled(instance=None) -> bool:
    """
    Check if OTel sampling is enabled (for high-volume operations).
    
    Args:
        instance: Optional CommonPlan instance to get constants from
    
    Returns:
        True if sampling is enabled, False otherwise
    """
    value = _get_config_value("OTEL_SAMPLING_ENABLED", "true", instance)
    if isinstance(value, bool):
        return value
    return str(value).lower() == "true"

def get_otel_sampling_rate(instance=None) -> float:
    """
    Get OTel sampling rate (0.0 to 1.0).
    
    Args:
        instance: Optional CommonPlan instance to get constants from
    
    Returns:
        Sampling rate as float
    """
    value = _get_config_value("OTEL_SAMPLING_RATE", "1.0", instance)
    return float(value)

