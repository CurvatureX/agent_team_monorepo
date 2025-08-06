"""
Node ID Generator Utility

This module provides functionality for generating and validating workflow node IDs.
"""

import re
import uuid
from typing import List, Set, Dict, Any


class NodeIdGenerator:
    """
    Utility class for generating and managing node IDs.
    
    ID Format: {type}_{subtype}_{short_uuid}
    Example: trigger_manual_a3b4c5d6
    """
    
    # Valid node ID pattern
    NODE_ID_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]*$')
    
    # Reserved keywords that cannot be used as node IDs
    RESERVED_IDS = {
        'start', 'end', 'input', 'output', 'context', 
        'workflow', 'execution', 'node', 'connection'
    }
    
    @classmethod
    def ensure_unique_node_ids(cls, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ensure all nodes have unique IDs.
        
        Rules:
        1. If node has valid, unique ID -> keep it
        2. If node has no ID or empty ID -> generate new ID
        3. If node ID is duplicate -> generate new ID for duplicate
        4. If node ID is reserved -> generate new ID
        
        Args:
            nodes: List of node dictionaries
            
        Returns:
            List of nodes with unique IDs
        """
        seen_ids: Set[str] = set()
        
        for node in nodes:
            current_id = node.get('id') or ''
            if current_id:
                current_id = current_id.strip()
            
            # Check if ID needs to be generated
            needs_new_id = (
                not current_id or 
                current_id in seen_ids or 
                current_id.lower() in cls.RESERVED_IDS or
                not cls.is_valid_node_id(current_id)
            )
            
            if needs_new_id:
                # Generate new ID
                new_id = cls.generate_node_id(
                    node_type=node.get('type', 'UNKNOWN'),
                    node_subtype=node.get('subtype', 'default'),
                    node_name=node.get('name', 'Unnamed Node'),
                    existing_ids=seen_ids
                )
                node['id'] = new_id
                seen_ids.add(new_id)
            else:
                # Keep existing valid ID
                seen_ids.add(current_id)
        
        return nodes
    
    @classmethod
    def generate_node_id(
        cls,
        node_type: str,
        node_subtype: str,
        node_name: str,
        existing_ids: Set[str]
    ) -> str:
        """
        Generate a unique node ID.
        
        Format: {type}_{subtype}_{short_uuid}
        
        Args:
            node_type: Node type (e.g., TRIGGER, ACTION)
            node_subtype: Node subtype (e.g., MANUAL, HTTP_REQUEST)
            node_name: Node display name
            existing_ids: Set of already used IDs
            
        Returns:
            Generated unique node ID
        """
        # Clean and normalize type and subtype
        clean_type = cls._clean_identifier(node_type)
        clean_subtype = cls._clean_identifier(node_subtype)
        
        # Generate base ID
        base_id = f"{clean_type}_{clean_subtype}"
        
        # Add short UUID to ensure uniqueness
        attempts = 0
        max_attempts = 100
        
        while attempts < max_attempts:
            short_uuid = uuid.uuid4().hex[:8]
            node_id = f"{base_id}_{short_uuid}"
            
            if node_id not in existing_ids and node_id.lower() not in cls.RESERVED_IDS:
                return node_id
            
            attempts += 1
        
        # Fallback: use full UUID if we can't generate unique ID
        return f"node_{uuid.uuid4().hex}"
    
    @classmethod
    def is_valid_node_id(cls, node_id: str) -> bool:
        """
        Check if a node ID is valid.
        
        Rules:
        - Must match pattern: start with letter/underscore, followed by letters/numbers/underscore/hyphen
        - Length between 3 and 100 characters
        - Not a reserved keyword
        - No spaces or special characters
        
        Args:
            node_id: Node ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not node_id or not isinstance(node_id, str):
            return False
        
        # Check length
        if len(node_id) < 3 or len(node_id) > 100:
            return False
        
        # Check pattern
        if not cls.NODE_ID_PATTERN.match(node_id):
            return False
        
        # Check reserved keywords
        if node_id.lower() in cls.RESERVED_IDS:
            return False
        
        return True
    
    @classmethod
    def _clean_identifier(cls, text: str) -> str:
        """
        Clean text to be used as part of an identifier.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned identifier
        """
        if not text:
            return "unknown"
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove common suffixes
        text = text.replace('_node', '').replace('-node', '')
        
        # Replace spaces and special characters with underscore
        text = re.sub(r'[^a-z0-9]+', '_', text)
        
        # Remove leading/trailing underscores
        text = text.strip('_')
        
        # Ensure it starts with a letter
        if text and text[0].isdigit():
            text = 'n' + text
        
        return text or "unknown"
    
    @classmethod
    def migrate_legacy_ids(cls, nodes: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Migrate legacy node IDs to new format while maintaining references.
        
        Args:
            nodes: List of nodes with potentially legacy IDs
            
        Returns:
            Mapping of old IDs to new IDs
        """
        id_mapping = {}
        seen_ids: Set[str] = set()
        
        for node in nodes:
            old_id = node.get('id', '')
            
            # Generate new ID
            new_id = cls.generate_node_id(
                node_type=node.get('type', 'UNKNOWN'),
                node_subtype=node.get('subtype', 'default'),
                node_name=node.get('name', 'Unnamed Node'),
                existing_ids=seen_ids
            )
            
            # Update mapping
            id_mapping[old_id] = new_id
            seen_ids.add(new_id)
            
            # Update node
            node['id'] = new_id
        
        return id_mapping
    
    @classmethod
    def create_name_to_id_mapping(cls, nodes: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Create a mapping from node names to node IDs.
        
        Args:
            nodes: List of node dictionaries with 'name' and 'id' fields
            
        Returns:
            Dictionary mapping node names to node IDs
        """
        return {node['name']: node['id'] for node in nodes if node.get('name') and node.get('id')}
    
    @classmethod
    def resolve_connection_references(
        cls,
        connections: Dict[str, Any],
        name_to_id_mapping: Dict[str, str],
        node_ids: Set[str]
    ) -> Dict[str, Any]:
        """
        Resolve connection references from names to IDs.
        
        This method handles both name-based and ID-based references:
        - If a reference matches a node name, it's converted to the corresponding ID
        - If a reference is already an ID, it's kept as is
        - Invalid references are preserved (will be caught by validation)
        
        Args:
            connections: Connection configuration (may use names or IDs)
            name_to_id_mapping: Mapping from node names to IDs
            node_ids: Set of all valid node IDs
            
        Returns:
            Updated connections using only IDs
        """
        updated_connections = {}
        
        for source_ref, connection_data in connections.items():
            # Resolve source reference (name or ID) to ID
            source_id = source_ref
            if source_ref in name_to_id_mapping:
                source_id = name_to_id_mapping[source_ref]
            elif source_ref not in node_ids:
                # Keep the reference as is (validation will catch invalid refs)
                pass
            
            # Update target references in connections
            updated_connection_data = {
                "connection_types": {}
            }
            
            for conn_type, conn_list in connection_data.get("connection_types", {}).items():
                updated_conn_list = {
                    "connections": []
                }
                
                for conn in conn_list.get("connections", []):
                    updated_conn = dict(conn)
                    target_ref = conn.get("node")
                    
                    # Resolve target reference to ID
                    if target_ref in name_to_id_mapping:
                        updated_conn["node"] = name_to_id_mapping[target_ref]
                    # else: keep as is (already an ID or invalid)
                    
                    updated_conn_list["connections"].append(updated_conn)
                
                updated_connection_data["connection_types"][conn_type] = updated_conn_list
            
            updated_connections[source_id] = updated_connection_data
        
        return updated_connections
    
    @classmethod
    def update_connection_references(
        cls,
        connections: Dict[str, Any],
        id_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Update connection references after ID migration.
        
        Args:
            connections: Connection configuration
            id_mapping: Mapping of old IDs to new IDs
            
        Returns:
            Updated connections
        """
        updated_connections = {}
        
        for source_id, connection_data in connections.items():
            # Update source ID
            new_source_id = id_mapping.get(source_id, source_id)
            
            # Update target IDs in connections
            updated_connection_data = {
                "connection_types": {}
            }
            
            for conn_type, conn_list in connection_data.get("connection_types", {}).items():
                updated_conn_list = {
                    "connections": []
                }
                
                for conn in conn_list.get("connections", []):
                    updated_conn = dict(conn)
                    target_id = conn.get("node")
                    if target_id in id_mapping:
                        updated_conn["node"] = id_mapping[target_id]
                    
                    updated_conn_list["connections"].append(updated_conn)
                
                updated_connection_data["connection_types"][conn_type] = updated_conn_list
            
            updated_connections[new_source_id] = updated_connection_data
        
        return updated_connections