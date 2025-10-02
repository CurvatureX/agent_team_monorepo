"""
Workflow graph utilities for v2 engine.
"""

from __future__ import annotations

import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models.workflow_new import Connection, Workflow
from workflow_engine_v2.core.exceptions import CycleError


class WorkflowGraph:
    """Directed graph built from Workflow.connections.

    - Nodes are identified by node.id
    - Edges are (from_node -> to_node) annotated with (output_key, conversion_function)
    """

    def __init__(self, workflow: Workflow):
        self.workflow = workflow
        self.nodes = {n.id: n for n in workflow.nodes}
        # Edge tuple: (to_node, output_key, conversion_function)
        # output_key: which output from source node to use (e.g., 'main', 'true', 'false')
        self.adjacency_list: Dict[str, List[Tuple[str, str, Optional[str]]]] = defaultdict(list)
        self.reverse_adjacency_list: Dict[str, List[Tuple[str, str, Optional[str]]]] = defaultdict(
            list
        )
        self._in_degree: Dict[str, int] = {node_id: 0 for node_id in self.nodes.keys()}
        self._build()

    def _build(self) -> None:
        for c in self.workflow.connections:
            # Use output_key if available (new), fallback to from_port (legacy compatibility)
            output_key = getattr(c, "output_key", None) or getattr(c, "from_port", "result")

            self.adjacency_list[c.from_node].append((c.to_node, output_key, c.conversion_function))
            self.reverse_adjacency_list[c.to_node].append(
                (c.from_node, output_key, c.conversion_function)
            )
            if c.to_node in self._in_degree:
                self._in_degree[c.to_node] += 1

    def predecessors(self, node_id: str) -> List[Tuple[str, str, Optional[str]]]:
        """Get predecessor nodes: [(from_node, output_key, conversion_function), ...]"""
        return self.reverse_adjacency_list.get(node_id, [])

    def successors(self, node_id: str) -> List[Tuple[str, str, Optional[str]]]:
        """Get successor nodes: [(to_node, output_key, conversion_function), ...]"""
        return self.adjacency_list.get(node_id, [])

    def in_degree(self, node_id: str) -> int:
        return self._in_degree.get(node_id, 0)

    def sources(self) -> List[str]:
        # Prefer configured triggers if available; otherwise in-degree==0
        if self.workflow.triggers:
            return list(self.workflow.triggers)
        return [node_id for node_id, deg in self._in_degree.items() if deg == 0]

    def topo_order(self) -> List[str]:
        """Kahn topological order with cycle detection.

        Returns a list of node IDs in a valid execution order. If a cycle is
        detected, raises CycleError.
        """
        in_degree_map = dict(self._in_degree)
        queue = deque([node_id for node_id, deg in in_degree_map.items() if deg == 0])
        order: List[str] = []
        while queue:
            current_node = queue.popleft()
            order.append(current_node)
            for successor, _output_key, _conversion in self.adjacency_list.get(current_node, []):
                in_degree_map[successor] -= 1
                if in_degree_map[successor] == 0:
                    queue.append(successor)
        if len(order) != len(self.nodes):
            raise CycleError("Workflow graph contains a cycle; cannot compute topo order")
        return order

    def reachable_from(self, roots: Iterable[str]) -> Set[str]:
        seen: Set[str] = set()
        queue = deque(roots)
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            for successor, _output_key, _conv in self.adjacency_list.get(current, []):
                if successor not in seen:
                    queue.append(successor)
        return seen


__all__ = ["WorkflowGraph"]
