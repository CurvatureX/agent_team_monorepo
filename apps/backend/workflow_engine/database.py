"""
Simple database operations for Workflow Engine

Clean, simple database interface using Supabase.
"""

import logging
import ssl
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure SSL for better compatibility
import urllib3
from supabase import Client, create_client

from config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class Database:
    """Simple database interface"""

    def __init__(self):
        """Initialize database connection"""
        self.client: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Supabase client"""
        try:
            if settings.supabase_url and settings.supabase_secret_key:
                self.client = create_client(settings.supabase_url, settings.supabase_secret_key)
                logger.info("✅ Database client initialized")
            else:
                logger.error("❌ Missing Supabase configuration")
        except Exception as e:
            logger.error(f"❌ Failed to initialize database client: {e}")
            self.client = None

    async def test_connection(self) -> bool:
        """Test database connection with DNS and SSL error handling"""
        try:
            if not self.client:
                raise Exception("Database client not initialized")

            # Simple test query with retry for DNS, SSL, and network issues
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = self.client.table("workflows").select("id").limit(1).execute()
                    logger.info("✅ Database connection test successful")
                    return True
                except Exception as err:
                    error_str = str(err).lower()
                    # Handle various network issues gracefully
                    if any(
                        keyword in error_str
                        for keyword in [
                            "ssl",
                            "eof",
                            "connection",
                            "timeout",
                            "dns",
                            "resolve",
                            "name resolution",
                            "temporary failure",
                            "network",
                        ]
                    ):
                        logger.warning(
                            f"⚠️  Network connection attempt {attempt + 1} failed: {err}"
                        )
                        if attempt < max_retries - 1:
                            import time

                            time.sleep(2)  # Longer pause for network issues
                            continue
                        else:
                            logger.warning(
                                "⚠️  All network connection attempts failed - service will run with limited functionality"
                            )
                            return False
                    else:
                        # Re-raise non-network errors
                        raise

        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False

    async def create_execution_record(
        self, execution_id: str, workflow_id: str, user_id: str, status: str
    ) -> Dict[str, Any]:
        """Create execution record"""
        try:
            if not self.client:
                raise Exception("Database client not initialized")

            now = datetime.now().isoformat()
            execution_data = {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": status,
                "triggered_by": user_id,
                "created_at": now,
                "updated_at": now,
            }

            # Use SupabaseWorkflowRepository to avoid client corruption issues
            from services.supabase_repository import SupabaseWorkflowRepository

            repository = SupabaseWorkflowRepository()
            result = await repository.create_execution(execution_data)
            logger.info(f"✅ Created execution record: {execution_id}")
            return result or {}

        except Exception as e:
            logger.error(f"❌ Failed to create execution record: {e}")
            raise

    async def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution status"""
        try:
            # Use SupabaseWorkflowRepository to avoid client corruption issues
            from services.supabase_repository import SupabaseWorkflowRepository

            repository = SupabaseWorkflowRepository()
            return await repository.get_execution(execution_id)

        except Exception as e:
            logger.error(f"❌ Failed to get execution status: {e}")
            return None

    async def update_execution_status(
        self, execution_id: str, status: str, error_message: Optional[str] = None
    ):
        """Update execution status"""
        try:
            if not self.client:
                raise Exception("Database client not initialized")

            update_data = {
                "status": status,
                "updated_at": datetime.now().isoformat(),
            }

            if error_message:
                update_data["error_message"] = error_message

            # Use SupabaseWorkflowRepository to avoid client corruption issues
            from services.supabase_repository import SupabaseWorkflowRepository

            repository = SupabaseWorkflowRepository()
            await repository.update_execution(execution_id, update_data)
            logger.info(f"✅ Updated execution status: {execution_id} -> {status}")

        except Exception as e:
            logger.error(f"❌ Failed to update execution status: {e}")

    async def list_workflows(self) -> List[Dict[str, Any]]:
        """List workflows - return all workflows with proper ordering"""
        try:
            if not self.client:
                raise Exception("Database client not initialized")

            # Get all workflows, ordered by deployment status (DEPLOYED first) and updated_at
            result = (
                self.client.table("workflows")
                .select("*")
                .order("deployment_status", desc=True)
                .order("updated_at", desc=True)
                .limit(1000)
                .execute()
            )
            workflows = result.data or []

            logger.info(f"✅ Retrieved {len(workflows)} workflows")
            return workflows

        except Exception as e:
            logger.error(f"❌ Failed to list workflows: {e}")
            return []

    async def get_workflow_executions(
        self, workflow_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get execution history for a specific workflow"""
        try:
            if not self.client:
                raise Exception("Database client not initialized")

            # Query executions for the workflow, ordered by most recent first
            result = (
                self.client.table("workflow_executions")
                .select("*")
                .eq("workflow_id", workflow_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            executions = result.data or []

            logger.info(f"✅ Retrieved {len(executions)} executions for workflow {workflow_id}")
            return executions

        except Exception as e:
            logger.error(f"❌ Failed to get workflow executions: {e}")
            return []
