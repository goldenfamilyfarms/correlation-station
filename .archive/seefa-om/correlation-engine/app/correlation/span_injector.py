"""
Span Injector - Exports synthetic spans to Tempo

Handles the export of synthetic bridge spans created by the TraceSynthesizer.
"""

import logging
from typing import Dict, List
import httpx
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
from opentelemetry.proto.common.v1.common_pb2 import KeyValue, AnyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

logger = logging.getLogger(__name__)


class SpanInjector:
    """
    Exports synthetic spans to Tempo via OTLP

    Converts dict-based span representations to OTLP protobuf
    and exports them to Tempo.
    """

    def __init__(self, tempo_endpoint: str = "http://tempo:4318"):
        """
        Initialize span injector

        Args:
            tempo_endpoint: Tempo OTLP HTTP endpoint
        """
        self.tempo_endpoint = tempo_endpoint.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def inject_span(self, span_dict: Dict) -> bool:
        """
        Inject a single synthetic span into Tempo

        Args:
            span_dict: Span dictionary from TraceSynthesizer.create_bridge_span()

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert dict to OTLP protobuf
            otlp_request = self._dict_to_otlp(span_dict)

            # Export to Tempo
            response = await self.client.post(
                f"{self.tempo_endpoint}/v1/traces",
                content=otlp_request.SerializeToString(),
                headers={"Content-Type": "application/x-protobuf"},
            )

            if response.status_code == 200:
                logger.debug(f"Successfully injected synthetic span: {span_dict['name']}")
                return True
            else:
                logger.error(
                    f"Failed to inject span: status={response.status_code}, "
                    f"response={response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error injecting span: {e}", exc_info=True)
            return False

    async def inject_spans(self, span_dicts: List[Dict]) -> int:
        """
        Inject multiple synthetic spans

        Args:
            span_dicts: List of span dictionaries

        Returns:
            Number of successfully injected spans
        """
        success_count = 0
        for span_dict in span_dicts:
            if await self.inject_span(span_dict):
                success_count += 1

        logger.info(f"Injected {success_count}/{len(span_dicts)} synthetic spans")
        return success_count

    def _dict_to_otlp(self, span_dict: Dict) -> ExportTraceServiceRequest:
        """
        Convert span dict to OTLP protobuf

        Args:
            span_dict: Span dictionary

        Returns:
            OTLP ExportTraceServiceRequest
        """
        # Create span
        span = Span()

        # Trace and span IDs (hex string → bytes)
        span.trace_id = bytes.fromhex(span_dict["trace_id"])
        span.span_id = bytes.fromhex(span_dict["span_id"])
        if span_dict.get("parent_span_id"):
            span.parent_span_id = bytes.fromhex(span_dict["parent_span_id"])

        # Name and kind
        span.name = span_dict["name"]
        span.kind = span_dict.get("kind", 3)  # Default INTERNAL

        # Timestamps
        span.start_time_unix_nano = span_dict["start_time_unix_nano"]
        span.end_time_unix_nano = span_dict["end_time_unix_nano"]

        # Attributes
        for key, value in span_dict.get("attributes", {}).items():
            kv = span.attributes.add()
            kv.key = key
            if isinstance(value, bool):
                kv.value.bool_value = value
            elif isinstance(value, int):
                kv.value.int_value = value
            elif isinstance(value, float):
                kv.value.double_value = value
            else:
                kv.value.string_value = str(value)

        # Links
        for link_dict in span_dict.get("links", []):
            link = span.links.add()
            link.trace_id = bytes.fromhex(link_dict["trace_id"])
            link.span_id = bytes.fromhex(link_dict["span_id"])

            for key, value in link_dict.get("attributes", {}).items():
                kv = link.attributes.add()
                kv.key = key
                kv.value.string_value = str(value)

        # Status
        if span_dict.get("status"):
            span.status.code = span_dict["status"].get("code", 1)
            if span_dict["status"].get("message"):
                span.status.message = span_dict["status"]["message"]

        # Wrap in ScopeSpans
        scope_spans = ScopeSpans()
        scope_spans.spans.append(span)

        # Wrap in ResourceSpans with synthetic resource
        resource_spans = ResourceSpans()
        resource_spans.scope_spans.append(scope_spans)

        # Add resource attributes
        resource = resource_spans.resource
        self._add_resource_attribute(resource, "service.name", "correlation-station")
        self._add_resource_attribute(resource, "telemetry.sdk.name", "correlation-station")
        self._add_resource_attribute(resource, "span.type", "synthetic")

        # Create request
        request = ExportTraceServiceRequest()
        request.resource_spans.append(resource_spans)

        return request

    def _add_resource_attribute(self, resource: Resource, key: str, value: str):
        """Helper to add resource attribute"""
        kv = resource.attributes.add()
        kv.key = key
        kv.value.string_value = value

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
