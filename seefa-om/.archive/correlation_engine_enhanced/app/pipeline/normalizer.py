"""Log normalization - converts various formats to internal representation"""
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import structlog

from app.models import LogBatch, LogRecord

logger = structlog.get_logger()


class LogNormalizer:
    """Normalizes logs from various sources into a common format"""

    def __init__(self):
        self.syslog_patterns = [
            re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<service>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s*'
                r'(?P<message>.*)'
            ),
            re.compile(
                r'(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<service>\S+)\s*:\s*'
                r'(?P<message>.*)'
            ),
        ]
        self.trace_id_pattern = re.compile(r'\b([0-9a-f]{32}|[0-9a-f]{16})\b', re.IGNORECASE)

    def normalize_log_batch(self, batch: LogBatch) -> List[Dict[str, Any]]:
        """Normalize a log batch to internal format"""
        normalized = []
        for record in batch.records:
            norm_record = self._normalize_log_record(batch.resource.dict(), record)
            normalized.append(norm_record)
        return normalized

    def _normalize_log_record(self, resource: Dict[str, Any], record: LogRecord) -> Dict[str, Any]:
        """Normalize a single log record"""
        normalized = {
            "service": resource.get("service", "unknown"),
            "host": resource.get("host"),
            "env": resource.get("env", "dev"),
            "timestamp": record.timestamp,
            "severity": record.severity,
            "message": record.message,
            "labels": record.labels or {},
        }

        if record.trace_id:
            normalized["trace_id"] = record.trace_id
        elif self._extract_trace_id_from_message(record.message):
            normalized["trace_id"] = self._extract_trace_id_from_message(record.message)

        if record.span_id:
            normalized["span_id"] = record.span_id

        for attr in ['circuit_id', 'product_id', 'resource_id', 'resource_type_id', 'request_id']:
            if val := getattr(record, attr, None):
                normalized[attr] = val

        return normalized

    def _extract_trace_id_from_message(self, message: str) -> Optional[str]:
        """Extract trace ID from message text"""
        trace_patterns = [
            r'trace[-_]?id[=:]\s*([0-9a-f]{32})',
            r'traceid[=:]\s*([0-9a-f]{32})',
            r'trace[=:]\s*([0-9a-f]{32})',
        ]

        for pattern in trace_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        match = self.trace_id_pattern.search(message)
        if match:
            hex_str = match.group(1)
            if len(hex_str) == 32:
                return hex_str

        return None
