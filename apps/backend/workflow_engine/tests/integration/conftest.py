import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest

# Load environment variables from backend .env file
try:
    from dotenv import load_dotenv

    backend_env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if backend_env_path.exists():
        load_dotenv(backend_env_path)
        print(f"✅ Loaded environment variables from {backend_env_path}")
    else:
        print(f"⚠️  .env file not found at {backend_env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed, using existing environment variables")

# Ensure local module imports (when running from repo root)
CURRENT_DIR = os.path.dirname(__file__)
APP_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from main import app as fastapi_app  # type: ignore
from main import db as real_db  # type: ignore
from main import executor as real_executor


class InMemoryDB:
    """In-memory fake DB to avoid external dependencies in tests."""

    def __init__(self) -> None:
        self.client = object()  # sentinel to indicate "configured"
        self.executions: Dict[str, Dict[str, Any]] = {}
        self.workflows: Dict[str, Dict[str, Any]] = {}

    async def test_connection(self) -> bool:
        return True

    async def create_execution_record(
        self, execution_id: str, workflow_id: str, user_id: str, status: str
    ) -> Dict[str, Any]:
        rec = {
            "execution_id": execution_id,
            "workflow_id": workflow_id,
            "status": status,
            "triggered_by": user_id,
        }
        self.executions[execution_id] = rec
        return rec

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        return self.executions.get(execution_id)

    async def update_execution_status(
        self, execution_id: str, status: str, error_message: Optional[str] = None
    ) -> None:
        if execution_id in self.executions:
            self.executions[execution_id]["status"] = status
            if error_message:
                self.executions[execution_id]["error_message"] = error_message

    async def list_workflows(self) -> List[Dict[str, Any]]:
        return list(self.workflows.values())

    async def get_workflow_executions(
        self, workflow_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        return [e for e in self.executions.values() if e.get("workflow_id") == workflow_id][:limit]


class InMemoryLogService:
    """Minimal in-memory log service mock matching used interface in executor."""

    def __init__(self) -> None:
        self.logs: Dict[str, List[Dict[str, Any]]] = {}

    async def add_log_entry(self, entry: Any) -> None:
        # entry has to_dict() semantics not required here; we store a dict-like representation
        execution_id = getattr(entry, "execution_id", None)
        if execution_id is None:
            return
        self.logs.setdefault(execution_id, []).append(
            {
                "event_type": getattr(entry, "event_type", None),
                "message": getattr(entry, "message", None),
                "data": getattr(entry, "data", None),
                "level": getattr(entry, "level", None),
                "timestamp": getattr(entry, "timestamp", None),
            }
        )

    async def get_logs(
        self, execution_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        return list(self.logs.get(execution_id, []))[offset : offset + limit]


@pytest.fixture(autouse=True)
def _disable_external_env(monkeypatch: pytest.MonkeyPatch):
    """Ensure external providers don't call out; force mock behavior."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)


@pytest.fixture()
def in_memory_db(monkeypatch: pytest.MonkeyPatch) -> InMemoryDB:
    fake = InMemoryDB()
    # Patch main globals
    monkeypatch.setattr("main.db", fake, raising=True)
    # Patch executor.db instance too
    monkeypatch.setattr(real_executor, "db", fake, raising=True)
    return fake


@pytest.fixture()
def in_memory_logs(monkeypatch: pytest.MonkeyPatch) -> InMemoryLogService:
    from services import execution_log_service as els  # type: ignore

    fake = InMemoryLogService()
    # Patch the singleton getter to return our fake
    monkeypatch.setattr(els, "get_execution_log_service", lambda: fake, raising=True)
    # Also patch the already-created service on executor if any
    monkeypatch.setattr(real_executor, "log_service", fake, raising=True)
    return fake


@pytest.fixture()
def app_client_with_real_db(monkeypatch: pytest.MonkeyPatch):
    """httpx AsyncClient with real Supabase database and real API keys - REQUIRES credentials."""
    # Check if we have real Supabase credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SECRET_KEY")

    if not supabase_url or not supabase_key:
        pytest.fail(
            "❌ Real database integration tests require Supabase credentials.\n"
            "Set SUPABASE_URL and SUPABASE_SECRET_KEY environment variables.\n"
            "Example: SUPABASE_URL=https://xxx.supabase.co SUPABASE_SECRET_KEY=sb_secret_xxx pytest ..."
        )

    print("✅ Using real Supabase database and real API keys for integration tests")

    # Use real API keys - no mocking for comprehensive integration testing
    # The test environment should have these set for proper end-to-end testing

    transport = httpx.ASGITransport(app=fastapi_app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    try:
        yield client
    finally:
        asyncio.get_event_loop().run_until_complete(client.aclose())


@pytest.fixture()
def app_client(in_memory_db: InMemoryDB, in_memory_logs: InMemoryLogService):
    """httpx AsyncClient bound to the FastAPI app (no network)."""
    transport = httpx.ASGITransport(app=fastapi_app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    try:
        yield client
    finally:
        asyncio.get_event_loop().run_until_complete(client.aclose())


@pytest.fixture()
def patch_workflow_definition(monkeypatch: pytest.MonkeyPatch):
    """
    Returns a helper to patch executor.get_workflow_definition to a supplied structure.
    Usage: patch_workflow_definition(workflow_def)
    """

    def _apply(defn: Dict[str, Any]):
        async def _fake_get_def(workflow_id: str) -> Dict[str, Any]:
            # Ensure workflow id consistency
            d = dict(defn)
            d.setdefault("id", workflow_id)
            return d

        monkeypatch.setattr(real_executor, "get_workflow_definition", _fake_get_def, raising=True)

    return _apply
