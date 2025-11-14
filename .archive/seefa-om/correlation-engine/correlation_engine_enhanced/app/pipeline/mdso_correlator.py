"""MDSO-specific correlation logic"""
import structlog
from collections import defaultdict
from typing import Dict, List
from opentelemetry import trace

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class MDSOCorrelator:
    """Correlates MDSO logs and traces by circuit_id"""
    
    def correlate_by_circuit_id(
        self,
        logs: List[dict],
        traces: List[dict]
    ) -> Dict[str, Dict[str, List]]:
        """Correlate logs and traces by circuit_id
        
        This handles cases where trace_id is not available but circuit_id is
        """
        with tracer.start_as_current_span(
            "mdso.correlate_by_circuit_id",
            attributes={
                "log_count": len(logs),
                "trace_count": len(traces)
            }
        ) as span:
            by_circuit = defaultdict(lambda: {"logs": [], "traces": []})
            
            # Group logs by circuit_id
            for log in logs:
                if circuit_id := log.get("circuit_id"):
                    by_circuit[circuit_id]["logs"].append(log)
            
            # Group traces by circuit_id from attributes
            for trace_data in traces:
                attrs = trace_data.get("attributes", {})
                if circuit_id := attrs.get("mdso.circuit_id"):
                    by_circuit[circuit_id]["traces"].append(trace_data)
            
            span.set_attribute("circuits_correlated", len(by_circuit))
            
            logger.info(
                "mdso_correlation_complete",
                circuits=len(by_circuit),
                total_logs=len(logs),
                total_traces=len(traces)
            )
            
            return dict(by_circuit)
    
    def correlate_by_resource_id(
        self,
        logs: List[dict],
        traces: List[dict]
    ) -> Dict[str, Dict[str, List]]:
        """Correlate by MDSO resource_id"""
        with tracer.start_as_current_span("mdso.correlate_by_resource_id") as span:
            by_resource = defaultdict(lambda: {"logs": [], "traces": []})
            
            for log in logs:
                if resource_id := log.get("resource_id"):
                    by_resource[resource_id]["logs"].append(log)
            
            for trace_data in traces:
                attrs = trace_data.get("attributes", {})
                if resource_id := attrs.get("mdso.resource_id"):
                    by_resource[resource_id]["traces"].append(trace_data)
            
            span.set_attribute("resources_correlated", len(by_resource))
            return dict(by_resource)
    
    def enrich_with_mdso_context(self, correlation_event: dict) -> dict:
        """Enrich correlation event with MDSO-specific context"""
        with tracer.start_as_current_span("mdso.enrich_correlation"):
            # Extract MDSO attributes from logs
            logs = correlation_event.get("logs", [])
            if logs:
                first_log = logs[0]
                correlation_event["mdso_context"] = {
                    "circuit_id": first_log.get("circuit_id"),
                    "resource_id": first_log.get("resource_id"),
                    "product_type": first_log.get("product_type"),
                    "device_tid": first_log.get("device_tid"),
                    "orch_state": first_log.get("orch_state"),
                }
            
            return correlation_event
