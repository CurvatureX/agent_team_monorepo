"""
Node Specification API endpoints.

Provides APIs for querying node specifications, validating workflows,
and testing data mappings.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from shared.node_specs import node_spec_registry
from shared.node_specs.base import NodeSpec
from workflow_engine.workflow_engine.data_mapping import DataMappingProcessor
from workflow_engine.workflow_engine.data_mapping.context import ExecutionContext
from workflow_engine.workflow_engine.data_mapping.processor import DataMapping, MappingType

from shared.logging_config import get_logger
logger = get_logger(__name__)
router = APIRouter(prefix="/node-specs", tags=["Node Specifications"])


# Request/Response Models
class NodeTypeInfo(BaseModel):
    """Node type information."""

    node_type: str
    subtypes: List[str]
    description: str


class NodeSpecResponse(BaseModel):
    """Node specification response."""

    node_type: str
    subtype: str
    version: str
    description: str
    parameters: List[Dict]
    input_ports: List[Dict]
    output_ports: List[Dict]
    examples: Optional[List[Dict]] = None


class ValidationRequest(BaseModel):
    """Workflow validation request."""

    nodes: List[Dict]
    connections: Dict


class ValidationResponse(BaseModel):
    """Validation response."""

    valid: bool
    errors: List[str]
    warnings: List[str] = []


class ConnectionValidationRequest(BaseModel):
    """Connection validation request."""

    source_node: Dict
    source_port: str
    target_node: Dict
    target_port: str


class DataMappingTestRequest(BaseModel):
    """Data mapping test request."""

    mapping_config: Dict
    sample_data: Dict
    context: Optional[Dict] = None


class DataMappingTestResponse(BaseModel):
    """Data mapping test response."""

    success: bool
    transformed_data: Optional[Dict] = None
    error: Optional[str] = None


# API Endpoints
@router.get("/node-types", response_model=List[NodeTypeInfo])
async def get_node_types():
    """Get all available node types and their subtypes."""
    try:
        node_types = node_spec_registry.get_node_types()
        result = []

        for node_type, subtypes in node_types.items():
            # Get a sample spec for description
            sample_spec = node_spec_registry.get_spec(node_type, subtypes[0]) if subtypes else None
            description = sample_spec.description if sample_spec else f"{node_type} nodes"

            result.append(
                NodeTypeInfo(node_type=node_type, subtypes=subtypes, description=description)
            )

        return result

    except Exception as e:
        logger.error(f"Error getting node types: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/node-types/{node_type}/{subtype}/spec", response_model=NodeSpecResponse)
async def get_node_spec(node_type: str, subtype: str):
    """Get detailed specification for a specific node type and subtype."""
    try:
        spec = node_spec_registry.get_spec(node_type, subtype)
        if not spec:
            raise HTTPException(
                status_code=404, detail=f"Node specification not found for {node_type}.{subtype}"
            )

        # Convert to response format
        return NodeSpecResponse(
            node_type=spec.node_type,
            subtype=spec.subtype,
            version=spec.version,
            description=spec.description,
            parameters=[
                {
                    "name": param.name,
                    "type": param.type.value,
                    "required": param.required,
                    "default_value": param.default_value,
                    "enum_values": param.enum_values,
                    "description": param.description,
                    "validation_pattern": param.validation_pattern,
                }
                for param in spec.parameters
            ],
            input_ports=[
                {
                    "name": port.name,
                    "type": port.type,
                    "required": port.required,
                    "description": port.description,
                    "max_connections": port.max_connections,
                    "validation_schema": port.validation_schema,
                }
                for port in spec.input_ports
            ],
            output_ports=[
                {
                    "name": port.name,
                    "type": port.type,
                    "description": port.description,
                    "max_connections": port.max_connections,
                    "validation_schema": port.validation_schema,
                }
                for port in spec.output_ports
            ],
            examples=spec.examples,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting node spec {node_type}.{subtype}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/workflows/validate", response_model=ValidationResponse)
async def validate_workflow(request: ValidationRequest):
    """Validate a workflow configuration against node specifications."""
    try:
        errors = []
        warnings = []

        # Validate each node against its specification
        for node_data in request.nodes:
            try:
                # Create a mock node object for validation
                mock_node = type(
                    "MockNode",
                    (),
                    {
                        "type": node_data.get("type"),
                        "subtype": node_data.get("subtype"),
                        "parameters": node_data.get("parameters", {}),
                        "input_ports": node_data.get("input_ports", []),
                        "output_ports": node_data.get("output_ports", []),
                        "id": node_data.get("id", "unknown"),
                    },
                )()

                node_errors = node_spec_registry.validate_node(mock_node)
                if node_errors:
                    errors.extend([f"Node {mock_node.id}: {error}" for error in node_errors])

            except Exception as e:
                errors.append(f"Node validation error: {str(e)}")

        # Validate connections
        for source_node_id, connections_map in request.connections.items():
            source_node = next((n for n in request.nodes if n.get("id") == source_node_id), None)
            if not source_node:
                errors.append(f"Source node not found: {source_node_id}")
                continue

            for connection_type, connection_list in connections_map.items():
                for connection in connection_list:
                    target_node_id = connection.get("node")
                    target_node = next(
                        (n for n in request.nodes if n.get("id") == target_node_id), None
                    )

                    if not target_node:
                        errors.append(f"Target node not found: {target_node_id}")
                        continue

                    # Validate port compatibility if port names are specified
                    source_port = connection.get("source_port", "main")
                    target_port = connection.get("target_port", "main")

                    # Create mock nodes for connection validation
                    mock_source = type(
                        "MockNode",
                        (),
                        {
                            "type": source_node.get("type"),
                            "subtype": source_node.get("subtype"),
                            "id": source_node.get("id"),
                        },
                    )()

                    mock_target = type(
                        "MockNode",
                        (),
                        {
                            "type": target_node.get("type"),
                            "subtype": target_node.get("subtype"),
                            "id": target_node.get("id"),
                        },
                    )()

                    connection_errors = node_spec_registry.validate_connection(
                        mock_source, source_port, mock_target, target_port
                    )
                    if connection_errors:
                        errors.extend(connection_errors)

        return ValidationResponse(valid=len(errors) == 0, errors=errors, warnings=warnings)

    except Exception as e:
        logger.error(f"Error validating workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/connections/validate", response_model=ValidationResponse)
async def validate_connection(request: ConnectionValidationRequest):
    """Validate compatibility between two node ports."""
    try:
        # Create mock nodes for validation
        mock_source = type(
            "MockNode",
            (),
            {
                "type": request.source_node.get("type"),
                "subtype": request.source_node.get("subtype"),
                "id": request.source_node.get("id", "source"),
            },
        )()

        mock_target = type(
            "MockNode",
            (),
            {
                "type": request.target_node.get("type"),
                "subtype": request.target_node.get("subtype"),
                "id": request.target_node.get("id", "target"),
            },
        )()

        errors = node_spec_registry.validate_connection(
            mock_source, request.source_port, mock_target, request.target_port
        )

        return ValidationResponse(valid=len(errors) == 0, errors=errors, warnings=[])

    except Exception as e:
        logger.error(f"Error validating connection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/data-mapping/test", response_model=DataMappingTestResponse)
async def test_data_mapping(request: DataMappingTestRequest):
    """Test data mapping transformation with sample data."""
    try:
        processor = DataMappingProcessor()

        # Convert mapping config to DataMapping object
        mapping_type = MappingType(request.mapping_config.get("type", "DIRECT"))

        # Create DataMapping object
        from workflow_engine.data_mapping.processor import (
            DataMapping,
            FieldMapping,
            FieldTransform,
            TransformType,
        )

        field_mappings = []
        if request.mapping_config.get("field_mappings"):
            for fm in request.mapping_config["field_mappings"]:
                transform = None
                if fm.get("transform"):
                    transform = FieldTransform(
                        type=TransformType(fm["transform"].get("type", "NONE")),
                        transform_value=fm["transform"].get("transform_value", ""),
                        options=fm["transform"].get("options", {}),
                    )

                field_mappings.append(
                    FieldMapping(
                        source_field=fm.get("source_field", ""),
                        target_field=fm.get("target_field", ""),
                        transform=transform,
                        required=fm.get("required", False),
                        default_value=fm.get("default_value"),
                    )
                )

        mapping = DataMapping(
            type=mapping_type,
            field_mappings=field_mappings,
            transform_script=request.mapping_config.get("transform_script"),
            static_values=request.mapping_config.get("static_values", {}),
            description=request.mapping_config.get("description", ""),
        )

        # Create execution context
        context = ExecutionContext(
            workflow_id="test", execution_id="test", variables=request.context or {}, metadata={}
        )

        # Transform data
        transformed_data = processor.transform_data(
            source_data=request.sample_data, mapping=mapping, context=context
        )

        return DataMappingTestResponse(success=True, transformed_data=transformed_data, error=None)

    except Exception as e:
        logger.error(f"Error testing data mapping: {e}")
        return DataMappingTestResponse(success=False, transformed_data=None, error=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint for node specifications service."""
    try:
        spec_count = len(node_spec_registry.list_all_specs())
        return {
            "status": "healthy",
            "loaded_specs": spec_count,
            "message": "Node specifications service is operational",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")
