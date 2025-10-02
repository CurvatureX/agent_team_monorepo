"""Execution repository abstractions.

Interfaces for persisting workflow executions/logs. Provide an in-memory impl.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional

from supabase import Client, create_client

# Add backend directory to path for absolute imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Use absolute imports
from shared.models import Execution


class ExecutionRepository:
    def save(self, execution: Execution) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def get(self, execution_id: str) -> Optional[Execution]:  # pragma: no cover - interface
        raise NotImplementedError

    def list(
        self, limit: int = 50, offset: int = 0
    ) -> list[Execution]:  # pragma: no cover - interface
        raise NotImplementedError


class InMemoryExecutionRepository(ExecutionRepository):
    def __init__(self) -> None:
        self._data: Dict[str, Execution] = {}

    def save(self, execution: Execution) -> None:
        self._data[execution.execution_id] = execution

    def get(self, execution_id: str) -> Optional[Execution]:
        return self._data.get(execution_id)

    def list(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        vals = list(self._data.values())
        # naive sort by start_time then execution_id
        vals.sort(key=lambda e: (e.start_time or 0, e.execution_id), reverse=True)
        return vals[offset : offset + limit]


class SupabaseExecutionRepository(ExecutionRepository):
    """Supabase-based execution repository for persistent storage."""

    def __init__(self) -> None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SECRET_KEY environment variables are required"
            )

        self._client: Client = create_client(supabase_url, supabase_key)

    def save(self, execution: Execution) -> None:
        """Save execution to Supabase database."""
        try:
            # Convert execution to dictionary for storage
            execution_data = {
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value
                if hasattr(execution.status, "value")
                else str(execution.status),
                "start_time": execution.start_time,
                "end_time": execution.end_time,
                "user_id": execution.user_id,
                "trigger_data": execution.trigger_data or {},
                "output_data": execution.output_data or {},
                "error_message": execution.error_message,
                "created_at": execution.created_at,
                "updated_at": execution.updated_at,
            }

            # Use upsert to handle both insert and update cases
            result = self._client.table("executions").upsert(execution_data).execute()

            if not result.data:
                raise Exception("Failed to save execution - no data returned")

        except Exception as e:
            raise Exception(f"Failed to save execution {execution.execution_id}: {str(e)}")

    def get(self, execution_id: str) -> Optional[Execution]:
        """Get execution by ID from Supabase database."""
        try:
            result = (
                self._client.table("executions")
                .select("*")
                .eq("execution_id", execution_id)
                .limit(1)
                .execute()
            )

            if not result.data:
                return None

            data = result.data[0]

            # Convert back to Execution object
            execution = Execution(
                execution_id=data["execution_id"],
                workflow_id=data["workflow_id"],
                status=data["status"],
                start_time=data.get("start_time"),
                end_time=data.get("end_time"),
                user_id=data.get("user_id"),
                trigger_data=data.get("trigger_data", {}),
                output_data=data.get("output_data", {}),
                error_message=data.get("error_message"),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
            )

            return execution

        except Exception as e:
            raise Exception(f"Failed to get execution {execution_id}: {str(e)}")

    def list(self, limit: int = 50, offset: int = 0) -> list[Execution]:
        """List executions with pagination from Supabase database."""
        try:
            result = (
                self._client.table("executions")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            executions = []
            for data in result.data:
                execution = Execution(
                    execution_id=data["execution_id"],
                    workflow_id=data["workflow_id"],
                    status=data["status"],
                    start_time=data.get("start_time"),
                    end_time=data.get("end_time"),
                    user_id=data.get("user_id"),
                    trigger_data=data.get("trigger_data", {}),
                    output_data=data.get("output_data", {}),
                    error_message=data.get("error_message"),
                    created_at=data.get("created_at"),
                    updated_at=data.get("updated_at"),
                )
                executions.append(execution)

            return executions

        except Exception as e:
            raise Exception(f"Failed to list executions: {str(e)}")


__all__ = ["ExecutionRepository", "InMemoryExecutionRepository", "SupabaseExecutionRepository"]
