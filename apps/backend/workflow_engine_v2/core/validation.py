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
from shared.models.workflow import Workflow
from workflow_engine_v2.core.spec import get_spec


class WorkflowValidationError(ValueError):
    pass


def validate_workflow(workflow: Workflow) -> None:
    import logging

    logger = logging.getLogger(__name__)
    errors: List[str] = []

    # Validate nodes
    node_map = {n.id: n for n in workflow.nodes}
    for n in workflow.nodes:
        ntype = n.type.value if hasattr(n.type, "value") else str(n.type)

        # Debug logging to see actual node data
        logger.debug(
            f"Validating node {n.id} ({ntype}.{n.subtype})\n"
            f"   Node object type: {type(n)}\n"
            f"   Configurations type: {type(n.configurations)}\n"
            f"   Configurations value: {n.configurations}\n"
            f"   Has configurations attr: {hasattr(n, 'configurations')}"
        )

        if not is_valid_node_subtype_combination(ntype, n.subtype):
            errors.append(f"Invalid type/subtype: {ntype}.{n.subtype} (node {n.id})")
        try:
            spec = get_spec(ntype, n.subtype)
            if hasattr(spec, "validate_configuration"):
                ok = spec.validate_configuration(n.configurations)
                if not ok:
                    # Log detailed validation failure info
                    required_keys = set()
                    if hasattr(spec, "configurations"):
                        for key, value in spec.configurations.items():
                            if isinstance(value, dict) and value.get("required", False):
                                required_keys.add(key)

                    present_keys = set(n.configurations.keys())
                    missing_keys = required_keys - present_keys

                    logger.error(
                        f"❌ Configuration validation failed for {ntype}.{n.subtype} (node {n.id})\n"
                        f"   Required keys: {required_keys}\n"
                        f"   Present keys: {present_keys}\n"
                        f"   Missing keys: {missing_keys}"
                    )
                    errors.append(f"Invalid configuration for node {n.id} ({ntype}.{n.subtype})")
            else:
                # Spec loaded but doesn't have validate_configuration (stub spec)
                logger.warning(
                    f"⚠️ Spec for {ntype}.{n.subtype} (node {n.id}) doesn't have validate_configuration - "
                    f"using stub spec (validation skipped)"
                )
        except Exception as e:
            logger.error(f"❌ Failed to get spec for {ntype}.{n.subtype} (node {n.id}): {e}")
            errors.append(f"Spec not found for {ntype}.{n.subtype} (node {n.id})")

        # Enforce attached_nodes semantics: only AI_AGENT may have attachments,
        # and only TOOL/MEMORY nodes may be attached
        try:
            if getattr(n, "attached_nodes", None):
                from shared.models.node_enums import NodeType as _NodeType

                ntype_enum = n.type if isinstance(n.type, _NodeType) else _NodeType(str(n.type))
                if ntype_enum != _NodeType.AI_AGENT:
                    errors.append(
                        f"Node {n.id} has attached_nodes but is not AI_AGENT (type={ntype_enum})"
                    )

                for aid in n.attached_nodes or []:
                    if aid not in node_map:
                        errors.append(f"Attached node id '{aid}' not found (referenced by {n.id})")
                        continue
                    attached = node_map[aid]
                    atype = (
                        attached.type
                        if isinstance(attached.type, _NodeType)
                        else _NodeType(str(attached.type))
                    )
                    if atype not in (_NodeType.TOOL, _NodeType.MEMORY):
                        errors.append(
                            f"Attached node '{aid}' must be TOOL or MEMORY (found {atype})"
                        )
        except Exception:
            # Do not fail hard on validation pass; collect as generic error
            errors.append(
                f"Failed to validate attached_nodes for node {n.id} due to unexpected error"
            )

    # Validate connections: nodes must exist
    for c in workflow.connections:
        if c.from_node not in node_map or c.to_node not in node_map:
            errors.append(f"Connection references unknown nodes: {c.from_node}->{c.to_node}")
            continue

    if errors:
        raise WorkflowValidationError("; ".join(errors))

    # Port validation removed - ports concept deprecated in favor of output_key
    # All connection routing now handled via output_key field

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
