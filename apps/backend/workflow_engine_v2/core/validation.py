"""Workflow validation utilities for v2 engine.

Checks:
- Node type/subtype combinations
- Node configuration against spec's required keys
- Connection ports exist on source/target nodes
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from shared.models.node_enums import is_valid_node_subtype_combination

# Use absolute imports
from shared.models.workflow_new import Workflow
from workflow_engine_v2.core.spec import get_spec


class WorkflowValidationError(ValueError):
    pass


def validate_workflow(workflow: Workflow) -> None:
    errors: List[str] = []

    # Validate nodes
    node_map = {n.id: n for n in workflow.nodes}
    for n in workflow.nodes:
        ntype = n.type.value if hasattr(n.type, "value") else str(n.type)
        if not is_valid_node_subtype_combination(ntype, n.subtype):
            errors.append(f"Invalid type/subtype: {ntype}.{n.subtype} (node {n.id})")
        try:
            spec = get_spec(ntype, n.subtype)
            if hasattr(spec, "validate_configuration"):
                ok = spec.validate_configuration(n.configurations)
                if not ok:
                    errors.append(f"Invalid configuration for node {n.id} ({ntype}.{n.subtype})")
        except Exception as e:
            errors.append(f"Spec not found for {ntype}.{n.subtype} (node {n.id})")

    # Validate connections: ports must exist
    in_conn_counts: Dict[str, Dict[str, int]] = {}
    out_conn_counts: Dict[str, Dict[str, int]] = {}
    for c in workflow.connections:
        if c.from_node not in node_map or c.to_node not in node_map:
            errors.append(f"Connection references unknown nodes: {c.from_node}->{c.to_node}")
            continue
        src = node_map[c.from_node]
        dst = node_map[c.to_node]
        if not any(p.id == c.from_port for p in src.output_ports):
            errors.append(f"Source port '{c.from_port}' not found on node {src.id}")
        if not any(p.id == c.to_port for p in dst.input_ports):
            errors.append(f"Target port '{c.to_port}' not found on node {dst.id}")
        # Count input/output connections for max_connections enforcement
        in_counts = in_conn_counts.setdefault(dst.id, {})
        in_counts[c.to_port] = in_counts.get(c.to_port, 0) + 1
        out_counts = out_conn_counts.setdefault(src.id, {})
        out_counts[c.from_port] = out_counts.get(c.from_port, 0) + 1

    if errors:
        raise WorkflowValidationError("; ".join(errors))

    # Enforce max_connections on ports
    errs2: List[str] = []
    for node in workflow.nodes:
        # Inputs
        for port in node.input_ports:
            maxc = getattr(port, "max_connections", 1)
            if maxc > 0:
                count = in_conn_counts.get(node.id, {}).get(port.id, 0)
                if count > maxc:
                    errs2.append(
                        f"Input port '{port.id}' on node {node.id} exceeds max_connections ({count}>{maxc})"
                    )
        # Outputs
        for port in node.output_ports:
            maxc = getattr(port, "max_connections", -1)
            if maxc > 0:
                count = out_conn_counts.get(node.id, {}).get(port.id, 0)
                if count > maxc:
                    errs2.append(
                        f"Output port '{port.id}' on node {node.id} exceeds max_connections ({count}>{maxc})"
                    )

    if errs2:
        raise WorkflowValidationError("; ".join(errs2))

    # Validate triggers: must exist and be TRIGGER nodes
    if workflow.triggers:
        for tid in workflow.triggers:
            if tid not in node_map:
                raise WorkflowValidationError(f"Trigger node id '{tid}' not found")
            tnode = node_map[tid]
            from shared.models.node_enums import NodeType

            try:
                ttype = (
                    tnode.type if isinstance(tnode.type, NodeType) else NodeType(str(tnode.type))
                )
            except Exception:
                ttype = None
            if ttype != NodeType.TRIGGER:
                raise WorkflowValidationError(
                    f"Node '{tid}' listed as trigger is not a TRIGGER node"
                )


__all__ = ["validate_workflow", "WorkflowValidationError"]
