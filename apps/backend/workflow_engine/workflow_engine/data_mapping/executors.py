"""
Connection Executors

Handles execution of connections between workflow nodes with data mapping.
"""

from shared.logging_config import get_logger

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .context import ExecutionContext
from .exceptions import ConnectionExecutionError
from .processor import DataMapping, DataMappingProcessor, MappingType


@dataclass
class Connection:
    """Connection definition with data mapping support."""

    node: str
    type: str = "MAIN"
    index: int = 0
    source_port: Optional[str] = None
    target_port: Optional[str] = None
    data_mapping: Optional[DataMapping] = None


@dataclass
class NodeExecutionResult:
    """Result of node execution."""

    node_id: str
    status: str
    output_data: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    port_outputs: Optional[Dict[str, Any]] = None

    @property
    def node(self):
        """Compatibility property for accessing node information."""
        return type("Node", (), {"id": self.node_id})()


class ConnectionExecutor:
    """Executes connections between workflow nodes with data mapping."""

    def __init__(self):
        self.data_mapper = DataMappingProcessor()
        self.logger = get_logger(__name__)

    def execute_connection(
        self,
        source_node_result: NodeExecutionResult,
        connection: Connection,
        target_node,
        context: ExecutionContext,
    ) -> Dict[str, Any]:
        """Execute connection with data mapping and validation."""

        try:
            self.logger.debug(
                f"Executing connection: {source_node_result.node_id} -> {connection.node}"
            )

            # 1. Get source port data
            source_data = self._get_port_data(source_node_result, connection.source_port or "main")

            if source_data is None:
                self.logger.warning(f"No data from source port: {connection.source_port}")
                return {}

            # 2. Apply data mapping
            if connection.data_mapping:
                try:
                    mapped_data = self.data_mapper.transform_data(
                        source_data,
                        connection.data_mapping,
                        context,
                        source_node=source_node_result.node,
                        target_node=target_node,
                        source_port=connection.source_port or "main",
                        target_port=connection.target_port or "main",
                    )
                    self.logger.debug(f"Data mapping applied: {connection.data_mapping.type.value}")
                except Exception as e:
                    self.logger.error(f"Data mapping failed: {e}")
                    raise ConnectionExecutionError(f"Data mapping failed: {str(e)}")
            else:
                # Default direct mapping with validation
                try:
                    mapped_data = self.data_mapper.transform_data(
                        source_data,
                        DataMapping(type=MappingType.DIRECT),
                        context,
                        source_node=source_node_result.node,
                        target_node=target_node,
                        source_port=connection.source_port or "main",
                        target_port=connection.target_port or "main",
                    )
                except Exception as e:
                    self.logger.error(f"Direct data mapping validation failed: {e}")
                    raise ConnectionExecutionError(
                        f"Direct data mapping validation failed: {str(e)}"
                    )

            # 3. Record data flow
            self._log_data_flow(source_node_result.node_id, target_node.id, connection, mapped_data)

            return mapped_data

        except Exception as e:
            self.logger.error(f"Connection execution failed: {e}")
            raise ConnectionExecutionError(f"Connection execution failed: {str(e)}")

    def execute_multiple_connections(
        self,
        source_node_result: NodeExecutionResult,
        connections: list,
        target_nodes: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Dict[str, Any]]:
        """Execute multiple connections from a single source node."""
        results = {}

        for connection in connections:
            try:
                target_node = target_nodes.get(connection.node)
                if not target_node:
                    self.logger.warning(f"Target node not found: {connection.node}")
                    continue

                mapped_data = self.execute_connection(
                    source_node_result, connection, target_node, context
                )

                results[connection.node] = mapped_data

            except Exception as e:
                self.logger.error(f"Connection to {connection.node} failed: {e}")
                results[connection.node] = {}

        return results

    def _get_port_data(
        self, node_result: NodeExecutionResult, port_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get data from specified output port."""

        if port_name == "main":
            return node_result.output_data

        # Support multi-port outputs
        if hasattr(node_result, "port_outputs") and node_result.port_outputs:
            return node_result.port_outputs.get(port_name)

        # Check if output_data contains port-specific data
        if isinstance(node_result.output_data, dict):
            port_data = node_result.output_data.get(f"port_{port_name}")
            if port_data is not None:
                return port_data

        return None

    def _log_data_flow(
        self, source_node_id: str, target_node_id: str, connection: Connection, data: Dict[str, Any]
    ):
        """Log data flow for debugging and monitoring."""
        mapping_type = connection.data_mapping.type.value if connection.data_mapping else "DIRECT"

        self.logger.info(
            f"Data flow: {source_node_id}[{connection.source_port or 'main'}] "
            f"-> {target_node_id}[{connection.target_port or 'main'}], "
            f"mapping: {mapping_type}, "
            f"data_size: {len(str(data))}"
        )

        # Log data keys for debugging
        if isinstance(data, dict):
            self.logger.debug(f"Data keys: {list(data.keys())}")


class BatchConnectionExecutor:
    """Batch executor for processing multiple connections efficiently."""

    def __init__(self):
        self.connection_executor = ConnectionExecutor()
        self.logger = get_logger(__name__)

    def execute_node_connections(
        self,
        source_results: Dict[str, NodeExecutionResult],
        connections_map: Dict[str, list],
        target_nodes: Dict[str, Any],
        context: ExecutionContext,
    ) -> Dict[str, Dict[str, Any]]:
        """Execute all connections for multiple source nodes."""

        all_results = {}

        for source_node_id, connections in connections_map.items():
            if source_node_id not in source_results:
                self.logger.warning(f"Source node result not found: {source_node_id}")
                continue

            source_result = source_results[source_node_id]

            try:
                node_results = self.connection_executor.execute_multiple_connections(
                    source_result, connections, target_nodes, context
                )

                all_results[source_node_id] = node_results

            except Exception as e:
                self.logger.error(f"Batch execution failed for node {source_node_id}: {e}")
                all_results[source_node_id] = {}

        return all_results

    def validate_connections(
        self,
        connections_map: Dict[str, list],
        source_nodes: Dict[str, Any],
        target_nodes: Dict[str, Any],
    ) -> list:
        """Validate all connections in the map."""

        errors = []

        for source_node_id, connections in connections_map.items():
            if source_node_id not in source_nodes:
                errors.append(f"Source node not found: {source_node_id}")
                continue

            for connection in connections:
                # Validate target node exists
                if connection.node not in target_nodes:
                    errors.append(f"Target node not found: {connection.node}")

                # Validate data mapping configuration
                if connection.data_mapping:
                    mapping_errors = self._validate_data_mapping(connection.data_mapping)
                    errors.extend(mapping_errors)

        return errors

    def _validate_data_mapping(self, mapping: DataMapping) -> list:
        """Validate data mapping configuration."""
        errors = []

        if mapping.type == MappingType.FIELD_MAPPING:
            for field_mapping in mapping.field_mappings:
                if not field_mapping.source_field:
                    errors.append("Field mapping missing source_field")
                if not field_mapping.target_field:
                    errors.append("Field mapping missing target_field")

        elif mapping.type == MappingType.TEMPLATE:
            if not mapping.transform_script:
                errors.append("Template mapping missing transform_script")

        elif mapping.type == MappingType.TRANSFORM:
            if not mapping.transform_script:
                errors.append("Transform mapping missing transform_script")

        return errors
