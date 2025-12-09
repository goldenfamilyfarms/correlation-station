"""
Trace Synthesizer - Creates synthetic parent spans to link disconnected traces

Handles the core correlation logic for bridging trace gaps when MDSO
doesn't propagate W3C Trace Context to Sense apps.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


@dataclass
class TraceSegment:
    """
    Represents a segment of a distributed trace

    A trace segment is a collection of related spans from a single service
    that can be correlated with other segments via business identifiers.
    """
    trace_id: str
    span_id: str
    service: str
    timestamp: datetime
    circuit_id: Optional[str] = None
    resource_id: Optional[str] = None
    product_id: Optional[str] = None
    resource_type_id: Optional[str] = None
    operation: Optional[str] = None
    attributes: Dict[str, any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp is datetime object"""
        if isinstance(self.timestamp, (int, float)):
            self.timestamp = datetime.utcfromtimestamp(self.timestamp)
        elif isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))


class TraceSynthesizer:
    """
    Links disconnected trace segments using correlation keys

    The synthesizer maintains a sliding window of trace segments and
    attempts to find parent-child relationships based on:
    1. Correlation key matching (circuit_id, resource_id, product_id)
    2. Temporal proximity (within correlation window)
    3. Service flow patterns (known call sequences)

    Example:
        MDSO creates resource (trace A) → calls Sense app (trace B)
        Since MDSO doesn't propagate trace context, we create synthetic
        bridge span linking trace A → trace B via circuit_id match.
    """

    def __init__(self, correlation_window_seconds: int = 60):
        """
        Initialize trace synthesizer

        Args:
            correlation_window_seconds: Time window for correlating segments
        """
        self.window = timedelta(seconds=correlation_window_seconds)
        self.segments: List[TraceSegment] = []
        self._correlation_stats = {
            "segments_added": 0,
            "parents_found": 0,
            "bridge_spans_created": 0,
        }

    def add_segment(self, segment: TraceSegment):
        """
        Add trace segment for correlation

        Args:
            segment: Trace segment to add
        """
        self.segments.append(segment)
        self._correlation_stats["segments_added"] += 1
        self._cleanup_old_segments()

        logger.debug(
            f"Added trace segment: service={segment.service}, "
            f"trace_id={segment.trace_id[:16]}..., "
            f"circuit_id={segment.circuit_id}"
        )

    def find_parent_trace(
        self,
        segment: TraceSegment,
        max_candidates: int = 5
    ) -> Optional[Tuple[TraceSegment, float]]:
        """
        Find parent trace segment based on correlation

        Scoring algorithm:
        - circuit_id match: +100 points
        - resource_id match: +80 points
        - product_id match: +60 points
        - temporal proximity: +40 points (within 10s) to 0 points (at window edge)
        - service flow pattern match: +50 points

        Args:
            segment: Child segment to find parent for
            max_candidates: Maximum number of candidates to consider

        Returns:
            Tuple of (parent_segment, confidence_score) or None
        """
        candidates = []

        for parent in self.segments:
            # Skip same service
            if parent.service == segment.service:
                continue

            # Skip if parent is newer than child (causality violation)
            if parent.timestamp > segment.timestamp:
                continue

            # Check if within correlation window
            time_diff = (segment.timestamp - parent.timestamp).total_seconds()
            if time_diff > self.window.total_seconds():
                continue

            # Calculate correlation score
            score = self._calculate_correlation_score(parent, segment, time_diff)

            if score > 0:
                candidates.append((parent, score, time_diff))

        if not candidates:
            return None

        # Sort by score (descending), then by time_diff (ascending)
        candidates.sort(key=lambda x: (-x[1], x[2]))

        # Return best match
        best_match = candidates[0]
        confidence = min(best_match[1] / 200.0, 1.0)  # Normalize to 0-1

        if confidence >= 0.5:  # Minimum confidence threshold
            self._correlation_stats["parents_found"] += 1
            logger.info(
                f"Found parent trace: parent={best_match[0].service}, "
                f"child={segment.service}, "
                f"confidence={confidence:.2f}, "
                f"time_diff={best_match[2]:.1f}s"
            )
            return (best_match[0], confidence)

        return None

    def _calculate_correlation_score(
        self,
        parent: TraceSegment,
        child: TraceSegment,
        time_diff: float
    ) -> float:
        """
        Calculate correlation score between two segments

        Args:
            parent: Potential parent segment
            child: Child segment
            time_diff: Time difference in seconds

        Returns:
            Correlation score (higher is better)
        """
        score = 0.0

        # Correlation key matching
        if child.circuit_id and parent.circuit_id == child.circuit_id:
            score += 100
        if child.resource_id and parent.resource_id == child.resource_id:
            score += 80
        if child.product_id and parent.product_id == child.product_id:
            score += 60

        # Temporal proximity (within 10s = full score, linear decay to window edge)
        if time_diff <= 10:
            score += 40
        elif time_diff <= self.window.total_seconds():
            decay_factor = 1 - (time_diff - 10) / (self.window.total_seconds() - 10)
            score += 40 * decay_factor

        # Service flow pattern matching
        if self._matches_known_flow(parent.service, child.service):
            score += 50

        return score

    def _matches_known_flow(self, parent_service: str, child_service: str) -> bool:
        """
        Check if service flow matches known patterns

        Known patterns:
        - beorn → mdso-scriptplan → arda
        - palantir → mdso-scriptplan
        - arda → granite
        """
        known_flows = {
            ("beorn", "mdso-scriptplan"),
            ("beorn", "palantir"),
            ("beorn", "arda"),
            ("palantir", "mdso-scriptplan"),
            ("palantir", "arda"),
            ("mdso-scriptplan", "arda"),
            ("mdso-scriptplan", "beorn"),
            ("mdso-scriptplan", "palantir"),
            ("arda", "granite"),
        }

        return (parent_service, child_service) in known_flows

    def create_bridge_span(
        self,
        parent: TraceSegment,
        child: TraceSegment,
        confidence: float
    ) -> Dict:
        """
        Create synthetic bridge span linking parent and child

        The bridge span:
        - Inherits parent's trace_id (links to parent trace)
        - Has parent's span_id as parent_span_id
        - Has a deterministic span_id (generated from parent+child)
        - Spans the time gap between parent end and child start
        - Contains link to child trace (for cross-trace navigation)

        Args:
            parent: Parent trace segment
            child: Child trace segment
            confidence: Correlation confidence score (0-1)

        Returns:
            OpenTelemetry span dict (ready for OTLP export)
        """
        # Generate deterministic span_id
        span_id_str = f"{parent.span_id}-{child.span_id}"
        span_id = hashlib.md5(span_id_str.encode()).hexdigest()[:16]

        # Create bridge span
        bridge_span = {
            "trace_id": parent.trace_id,
            "span_id": span_id,
            "parent_span_id": parent.span_id,
            "name": f"{parent.service}_to_{child.service}_bridge",
            "kind": 3,  # INTERNAL
            "start_time_unix_nano": int(parent.timestamp.timestamp() * 1e9),
            "end_time_unix_nano": int(child.timestamp.timestamp() * 1e9),
            "attributes": {
                # Bridge metadata
                "bridge.type": "synthetic",
                "bridge.parent_service": parent.service,
                "bridge.child_service": child.service,
                "bridge.parent_trace_id": parent.trace_id,
                "bridge.child_trace_id": child.trace_id,
                "synthetic": True,

                # Correlation metadata
                "correlation.method": "circuit_id_match",
                "correlation.confidence": confidence,
                "correlation.time_gap_seconds": (child.timestamp - parent.timestamp).total_seconds(),

                # Business identifiers
                "circuit_id": parent.circuit_id or child.circuit_id,
                "resource_id": parent.resource_id or child.resource_id,
                "product_id": parent.product_id or child.product_id,
                "resource_type_id": parent.resource_type_id or child.resource_type_id,
            },
            "links": [
                {
                    "trace_id": child.trace_id,
                    "span_id": child.span_id,
                    "attributes": {
                        "link.type": "follows_from",
                        "link.service": child.service,
                    }
                }
            ],
            "status": {
                "code": 1,  # OK
            }
        }

        self._correlation_stats["bridge_spans_created"] += 1

        logger.info(
            f"Created bridge span: {parent.service} → {child.service}, "
            f"confidence={confidence:.2f}, "
            f"gap={(child.timestamp - parent.timestamp).total_seconds():.1f}s"
        )

        return bridge_span

    def _cleanup_old_segments(self):
        """Remove segments outside correlation window"""
        now = datetime.utcnow()
        cutoff = now - self.window

        initial_count = len(self.segments)
        self.segments = [
            s for s in self.segments
            if s.timestamp >= cutoff
        ]

        removed = initial_count - len(self.segments)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old trace segments")

    def get_stats(self) -> Dict[str, int]:
        """
        Get correlation statistics

        Returns:
            Dictionary with stats
        """
        return {
            **self._correlation_stats,
            "active_segments": len(self.segments),
        }

    def reset_stats(self):
        """Reset correlation statistics"""
        self._correlation_stats = {
            "segments_added": 0,
            "parents_found": 0,
            "bridge_spans_created": 0,
        }
