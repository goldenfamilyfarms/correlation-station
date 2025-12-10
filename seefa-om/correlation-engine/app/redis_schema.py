"""
Redis Schema for Correlation Engine
Implements the keyspace design from correlation-enhancements.md
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import redis
from pydantic import BaseModel


class CircuitEvent(BaseModel):
    circuit_id: str
    date: str
    service_request_type: str
    product_name: str
    error_message: str
    cdnc_summary: str
    status: str


class TraceIndex(BaseModel):
    trace_id: str
    service: str
    status: str
    duration_ms: int
    resource_id: str
    correlation_id: str


class LogFileIndex(BaseModel):
    log_file: str
    trace_id: str
    process: str
    state: str


class RedisCorrelationStore:
    def __init__(self, redis_client: redis.Redis, ttl_hours: int = 48):
        self.client = redis_client
        self.ttl = timedelta(hours=ttl_hours)

    def _get_correlation_id(self, circuit_id: str, date: str) -> str:
        """Generate canonical correlation ID: <circuit_id>_<date>"""
        return f"{circuit_id}_{date}"

    def store_circuit_event(self, event: CircuitEvent) -> str:
        """Store circuit event in Redis HASH"""
        correlation_id = self._get_correlation_id(event.circuit_id, event.date)
        key = f"circuit:{correlation_id}"
        
        self.client.hset(key, mapping=event.dict())
        self.client.expire(key, self.ttl)
        
        return correlation_id

    def store_trace(self, trace: TraceIndex) -> None:
        """Store trace index in Redis HASH"""
        key = f"trace:{trace.trace_id}"
        
        self.client.hset(key, mapping=trace.dict())
        self.client.expire(key, self.ttl)

    def store_log_file(self, log: LogFileIndex) -> None:
        """Store log file index in Redis HASH"""
        key = f"logfile:{log.log_file}"
        
        self.client.hset(key, mapping=log.dict())
        self.client.expire(key, self.ttl)

    def store_traceback(self, trace_id: str, traceback_lines: List[str]) -> None:
        """Store extracted traceback as Redis LIST"""
        key = f"traceback:{trace_id}"
        
        self.client.delete(key)  # Clear existing
        self.client.rpush(key, *traceback_lines)
        self.client.expire(key, self.ttl)

    def add_to_error_group(self, normalized_error: str, correlation_id: str) -> None:
        """Add correlation_id to error group SET"""
        key = f"error_group:{normalized_error}"
        
        self.client.sadd(key, correlation_id)
        self.client.expire(key, self.ttl)

    def get_circuit_event(self, correlation_id: str) -> Optional[Dict]:
        """Retrieve circuit event by correlation ID"""
        key = f"circuit:{correlation_id}"
        data = self.client.hgetall(key)
        
        return {k.decode(): v.decode() for k, v in data.items()} if data else None

    def get_trace(self, trace_id: str) -> Optional[Dict]:
        """Retrieve trace by trace_id"""
        key = f"trace:{trace_id}"
        data = self.client.hgetall(key)
        
        return {k.decode(): v.decode() for k, v in data.items()} if data else None

    def get_traceback(self, trace_id: str) -> List[str]:
        """Retrieve traceback lines"""
        key = f"traceback:{trace_id}"
        lines = self.client.lrange(key, 0, -1)
        
        return [line.decode() for line in lines]

    def get_error_group(self, normalized_error: str) -> List[str]:
        """Get all correlation IDs in an error group"""
        key = f"error_group:{normalized_error}"
        members = self.client.smembers(key)
        
        return [m.decode() for m in members]

    def normalize_error(self, error_message: str) -> str:
        """Normalize error message for grouping"""
        # Remove specific IPs, timestamps, IDs
        import re
        normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '<IP>', error_message)
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', '<DATE>', normalized)
        normalized = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', '<UUID>', normalized)
        
        return normalized.lower().strip()
