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
        # Common syslog patterns
        self.syslog_patterns = [
            # Standard syslog: "2025-10-15T10:30:45.123Z hostname service[pid]: message"
            re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<service>\S+?)(?:\[(?P<pid>\d+)\])?\s*:\s*'
                r'(?P<message>.*)'
            ),
            # Alternative: "Oct 15 10:30:45 hostname service: message"
            re.compile(
                r'(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+'
                r'(?P<hostname>\S+)\s+'
                r'(?P<service>\S+)\s*:\s*'
                r'(?P<message>.*)'
            ),
        ]

        # Trace ID patterns (hex strings)
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
        # Start with resource info
        normalized = {
            "service": resource.get("service", "unknown"),
            "host": resource.get("host"),
            "env": resource.get("env", "dev"),
            "timestamp": record.timestamp,
            "severity": record.severity,
            "message": record.message,
            "labels": record.labels or {},
        }

        # Add trace context if present
        if record.trace_id:
            normalized["trace_id"] = record.trace_id
        elif self._extract_trace_id_from_message(record.message):
            normalized["trace_id"] = self._extract_trace_id_from_message(record.message)

        if record.span_id:
            normalized["span_id"] = record.span_id

        # Add custom attributes
        if record.circuit_id:
            normalized["circuit_id"] = record.circuit_id
        if record.product_id:
            normalized["product_id"] = record.product_id
        if record.resource_id:
            normalized["resource_id"] = record.resource_id
        if record.resource_type_id:
            normalized["resource_type_id"] = record.resource_type_id
        if record.request_id:
            normalized["request_id"] = record.request_id

        return normalized

    def normalize_syslog_line(self, line: str, service: str = "syslog") -> Dict[str, Any]:
        """Parse and normalize a raw syslog line"""
        # Try each pattern
        for pattern in self.syslog_patterns:
            match = pattern.match(line)
            if match:
                groups = match.groupdict()

                # Extract timestamp
                if 'timestamp' in groups:
                    timestamp = groups['timestamp']
                else:
                    # Construct timestamp from month/day/time
                    timestamp = self._construct_timestamp(
                        groups.get('month') or '',
                        groups.get('day') or '',
                        groups.get('time') or ''
                    )

                # Extract trace ID from message
                message = groups.get('message', line)
                trace_id = self._extract_trace_id_from_message(message)

                return {
                    "service": groups.get('service', service),
                    "host": groups.get('hostname'),
                    "env": "dev",
                    "timestamp": timestamp,
                    "severity": self._infer_severity(message),
                    "message": message,
                    "trace_id": trace_id,
                    "labels": {},
                }

        # If no pattern matched, return as-is with minimal parsing
        logger.warning("Failed to parse syslog line", line=line[:100])
        return {
            "service": service,
            "host": None,
            "env": "dev",
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "severity": "INFO",
            "message": line,
            "trace_id": self._extract_trace_id_from_message(line),
            "labels": {},
        }

    def _extract_trace_id_from_message(self, message: str) -> Optional[str]:
        """Extract trace ID from message text"""
        # Look for trace_id=<hex> or traceId=<hex> or similar
        trace_patterns = [
            r'trace[-_]?id[=:]\s*([0-9a-f]{32})',
            r'traceid[=:]\s*([0-9a-f]{32})',
            r'trace[=:]\s*([0-9a-f]{32})',
        ]

        for pattern in trace_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        # Look for any 32-char hex string (likely trace ID)
        match = self.trace_id_pattern.search(message)
        if match:
            hex_str = match.group(1)
            if len(hex_str) == 32:  # OpenTelemetry trace ID length
                return hex_str

        return None

    def _infer_severity(self, message: str) -> str:
        """Infer severity from message content"""
        message_lower = message.lower()

        if any(word in message_lower for word in ['error', 'fail', 'exception', 'critical']):
            return "ERROR"
        elif any(word in message_lower for word in ['warn', 'warning']):
            return "WARN"
        elif any(word in message_lower for word in ['debug', 'trace']):
            return "DEBUG"
        else:
            return "INFO"

    def _construct_timestamp(self, month: str, day: str, time: str) -> str:
        """Construct ISO timestamp from syslog date parts"""
        if not month or not day or not time:
            return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
            
        try:
            # Map month names to numbers
            months = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }

            month_num = months.get(month, '01')
            year = datetime.now(timezone.utc).year

            # Construct ISO timestamp
            return f"{year}-{month_num}-{day.zfill(2)}T{time}.000Z"
        except Exception:
            return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')