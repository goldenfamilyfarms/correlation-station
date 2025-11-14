"""
Shared global objects to avoid circular imports
"""
from prometheus_client import Counter

# Correlation engine will be initialized in main.py to avoid circular imports
correlation_engine = None

# Prometheus metrics
LOG_RECORDS_RECEIVED = Counter(
    'log_records_received_total',
    'Total number of log records received',
    ['source']
)