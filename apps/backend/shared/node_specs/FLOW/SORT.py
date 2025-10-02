"""
SORT Flow Node Specification

Simple sorter that orders data by a single field value.
Only field-based ascending/descending ordering is supported.
"""

from typing import Any, Dict, List

from ...models.node_enums import FlowSubtype, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec


class SortFlowSpec(BaseNodeSpec):
    """Sort flow node specification for data ordering and arrangement."""

    def __init__(self):
        super().__init__(
            type=NodeType.FLOW,
            subtype=FlowSubtype.SORT,
            name="Sort",
            description="Sort data based on one or multiple criteria with configurable ordering strategies",
            # Configuration parameters (simplified — field value sorting only)
            configurations={
                "sort_field": {
                    "type": "string",
                    "default": "",
                    "description": "要排序的字段（支持点号访问嵌套字段）",
                    "required": True,
                },
                "order": {
                    "type": "string",
                    "default": "asc",
                    "description": "排序顺序",
                    "required": False,
                    "options": ["asc", "desc"],
                },
                **COMMON_CONFIGS,
            },
            # Parameter schemas (preferred over legacy defaults)
            input_params={
                "data": {
                    "type": "array",
                    "default": [],
                    "description": "Input dataset to be sorted",
                    "required": True,
                },
                "metadata": {
                    "type": "object",
                    "default": {},
                    "description": "Optional metadata passed alongside data",
                    "required": False,
                },
                "sort_override": {
                    "type": "object",
                    "default": {},
                    "description": "Runtime override for sort configuration",
                    "required": False,
                },
            },
            output_params={
                "sorted_data": {
                    "type": "array",
                    "default": [],
                    "description": "Sorted dataset",
                    "required": False,
                },
                "sort_stats": {
                    "type": "object",
                    "default": {
                        "total_items": 0,
                        "items_sorted": 0,
                        "sort_time_ms": 0,
                        "comparisons_made": 0,
                    },
                    "description": "Sorting statistics and timing",
                    "required": False,
                },
                "original_indices": {
                    "type": "array",
                    "default": [],
                    "description": "Original indices of items prior to sort (if preserved)",
                    "required": False,
                },
            },
            # Port definitions
            input_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "any",
                    "description": "Data to be sorted",
                    "required": True,
                    "max_connections": 1,
                },
            ],
            output_ports=[
                {
                    "id": "main",
                    "name": "main",
                    "data_type": "any",
                    "description": "Sorted data output",
                    "required": True,
                    "max_connections": -1,
                }
            ],
            # Examples (simplified)
            examples=[
                {
                    "name": "Sort By Name (ASC)",
                    "description": "Sort array of objects by 'name' ascending",
                    "configurations": {"sort_field": "name", "order": "asc"},
                    "input_example": {
                        "main": [
                            {"name": "Charlie", "age": 30, "score": 85},
                            {"name": "Alice", "age": 25, "score": 92},
                            {"name": "Bob", "age": 35, "score": 78},
                            {"name": None, "age": 28, "score": 88},
                        ]
                    },
                    "expected_outputs": {
                        "sorted": [
                            {"name": "Alice", "age": 25, "score": 92},
                            {"name": "Bob", "age": 35, "score": 78},
                            {"name": "Charlie", "age": 30, "score": 85},
                            {"name": None, "age": 28, "score": 88},
                        ],
                        "metadata": {
                            "sort_stats": {
                                "total_items": 4,
                                "items_sorted": 4,
                                "sort_time_ms": 2,
                                "comparisons_made": 6,
                            },
                            "original_indices": [1, 2, 0, 3],
                        },
                    },
                },
                {
                    "name": "Sort By Score (DESC)",
                    "description": "Sort array of objects by 'score' descending",
                    "configurations": {"sort_field": "score", "order": "desc"},
                    "input_example": {
                        "main": [
                            {"name": "Alice", "score": 92},
                            {"name": "Bob", "score": 78},
                            {"name": "Charlie", "score": 85},
                        ]
                    },
                    "expected_outputs": {
                        "sorted": [
                            {"name": "Alice", "score": 92},
                            {"name": "Charlie", "score": 85},
                            {"name": "Bob", "score": 78},
                        ],
                        "metadata": {
                            "sort_stats": {
                                "total_items": 3,
                                "items_sorted": 3,
                                "sort_time_ms": 1,
                                "comparisons_made": 3,
                            }
                        },
                    },
                },
            ],
        )


# Export the specification instance
SORT_FLOW_SPEC = SortFlowSpec()
