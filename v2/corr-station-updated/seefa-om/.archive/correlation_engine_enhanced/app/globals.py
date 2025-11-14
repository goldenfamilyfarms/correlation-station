"""
Shared global objects to avoid circular imports
"""
from prometheus_client import Counter

correlation_engine = None

LOG_RECORDS_RECEIVED = Counter(
    'log_records_received_total',
    'Total number of log records received',
    ['source']
)
