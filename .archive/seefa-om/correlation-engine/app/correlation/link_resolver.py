"""
Link Resolver - Resolves trace links for visualization

Helps Grafana navigate between linked traces by maintaining
a mapping of trace relationships.
"""

import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class TraceLink:
    """Represents a link between two traces"""
    parent_trace_id: str
    child_trace_id: str
    link_type: str  # "follows_from", "child_of", "synthetic"
    timestamp: datetime
    circuit_id: Optional[str] = None
    confidence: float = 1.0


class LinkResolver:
    """
    Maintains and resolves trace links

    Provides fast lookup of trace relationships for:
    - Finding all traces related to a circuit_id
    - Finding parent/child traces
    - Building complete trace graphs
    """

    def __init__(self, retention_hours: int = 24):
        """
        Initialize link resolver

        Args:
            retention_hours: How long to keep trace links
        """
        self.retention = timedelta(hours=retention_hours)
        self._links: List[TraceLink] = []
        self._circuit_index: Dict[str, Set[str]] = {}  # circuit_id → set of trace_ids
        self._trace_index: Dict[str, List[TraceLink]] = {}  # trace_id → links

    def add_link(self, link: TraceLink):
        """
        Add a trace link

        Args:
            link: TraceLink to add
        """
        self._links.append(link)

        # Update circuit index
        if link.circuit_id:
            if link.circuit_id not in self._circuit_index:
                self._circuit_index[link.circuit_id] = set()
            self._circuit_index[link.circuit_id].add(link.parent_trace_id)
            self._circuit_index[link.circuit_id].add(link.child_trace_id)

        # Update trace index
        for trace_id in [link.parent_trace_id, link.child_trace_id]:
            if trace_id not in self._trace_index:
                self._trace_index[trace_id] = []
            self._trace_index[trace_id].append(link)

        self._cleanup_old_links()

    def find_related_traces(self, circuit_id: str) -> List[str]:
        """
        Find all traces related to a circuit_id

        Args:
            circuit_id: Circuit identifier

        Returns:
            List of trace IDs
        """
        return list(self._circuit_index.get(circuit_id, set()))

    def find_trace_chain(self, trace_id: str, max_depth: int = 10) -> List[TraceLink]:
        """
        Find complete chain of traces starting from a trace_id

        Uses BFS to traverse trace links.

        Args:
            trace_id: Starting trace ID
            max_depth: Maximum traversal depth

        Returns:
            List of TraceLinks forming the chain
        """
        visited = set()
        chain = []
        queue = [(trace_id, 0)]  # (trace_id, depth)

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth >= max_depth:
                continue

            visited.add(current_id)

            # Find links involving this trace
            links = self._trace_index.get(current_id, [])
            for link in links:
                if link not in chain:
                    chain.append(link)

                # Add connected traces to queue
                if link.parent_trace_id == current_id and link.child_trace_id not in visited:
                    queue.append((link.child_trace_id, depth + 1))
                elif link.child_trace_id == current_id and link.parent_trace_id not in visited:
                    queue.append((link.parent_trace_id, depth + 1))

        return chain

    def get_trace_graph(self, circuit_id: str) -> Dict:
        """
        Get complete trace graph for a circuit

        Returns a graph structure suitable for visualization.

        Args:
            circuit_id: Circuit identifier

        Returns:
            Dict with nodes and edges
        """
        trace_ids = self.find_related_traces(circuit_id)

        if not trace_ids:
            return {"nodes": [], "edges": []}

        # Build graph
        nodes = set(trace_ids)
        edges = []

        for trace_id in trace_ids:
            links = self._trace_index.get(trace_id, [])
            for link in links:
                edges.append({
                    "source": link.parent_trace_id,
                    "target": link.child_trace_id,
                    "type": link.link_type,
                    "confidence": link.confidence,
                })

        return {
            "nodes": [{"id": node} for node in nodes],
            "edges": edges,
            "circuit_id": circuit_id,
        }

    def _cleanup_old_links(self):
        """Remove links outside retention window"""
        now = datetime.utcnow()
        cutoff = now - self.retention

        initial_count = len(self._links)
        self._links = [link for link in self._links if link.timestamp >= cutoff]

        if len(self._links) < initial_count:
            # Rebuild indices
            self._rebuild_indices()

            removed = initial_count - len(self._links)
            logger.debug(f"Cleaned up {removed} old trace links")

    def _rebuild_indices(self):
        """Rebuild circuit and trace indices from scratch"""
        self._circuit_index.clear()
        self._trace_index.clear()

        for link in self._links:
            # Circuit index
            if link.circuit_id:
                if link.circuit_id not in self._circuit_index:
                    self._circuit_index[link.circuit_id] = set()
                self._circuit_index[link.circuit_id].add(link.parent_trace_id)
                self._circuit_index[link.circuit_id].add(link.child_trace_id)

            # Trace index
            for trace_id in [link.parent_trace_id, link.child_trace_id]:
                if trace_id not in self._trace_index:
                    self._trace_index[trace_id] = []
                self._trace_index[trace_id].append(link)

    def get_stats(self) -> Dict:
        """Get link resolver statistics"""
        return {
            "total_links": len(self._links),
            "circuits_tracked": len(self._circuit_index),
            "traces_tracked": len(self._trace_index),
        }
