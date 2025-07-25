"""
Startup health checks for API Gateway
"""

import asyncio
from typing import Any, Dict, List

import structlog
from supabase import create_client

from app.config import settings
from .config_validator import ConfigurationError, validate_environment_variables


# Import NodeKnowledgeClient only when needed to avoid circular imports
def get_node_knowledge_client():
    from clients.node_knowledge_client import NodeKnowledgeClient

    return NodeKnowledgeClient


logger = structlog.get_logger()


class StartupCheckError(Exception):
    """Startup check failure error"""

    def __init__(self, message: str, failed_checks: List[str]):
        self.message = message
        self.failed_checks = failed_checks
        super().__init__(message)


class StartupHealthChecker:
    """Performs startup health checks for all services"""

    def __init__(self):
        self.check_results: Dict[str, Dict[str, Any]] = {}

    async def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all startup health checks

        Returns:
            Dict with overall health check results

        Raises:
            StartupCheckError: If critical checks fail
        """
        logger.info("Starting startup health checks")

        overall_result = {
            "healthy": True,
            "checks": {},
            "errors": [],
            "warnings": [],
            "timestamp": None,
        }

        # 1. Configuration validation
        config_result = await self._check_configuration()
        overall_result["checks"]["configuration"] = config_result

        # 2. Supabase connection check (if MCP enabled)
        if settings.MCP_ENABLED:
            supabase_result = await self._check_supabase_connection()
            overall_result["checks"]["supabase"] = supabase_result
        else:
            overall_result["checks"]["supabase"] = {
                "healthy": True,
                "status": "skipped",
                "message": "MCP service disabled",
            }

        # 3. Node Knowledge service check (if MCP enabled)
        if settings.MCP_ENABLED:
            node_knowledge_result = await self._check_node_knowledge_service()
            overall_result["checks"]["node_knowledge"] = node_knowledge_result
        else:
            overall_result["checks"]["node_knowledge"] = {
                "healthy": True,
                "status": "skipped",
                "message": "MCP service disabled",
            }

        # Compile overall results
        failed_checks = []
        for check_name, result in overall_result["checks"].items():
            if not result.get("healthy", False) and result.get("status") != "skipped":
                failed_checks.append(check_name)
                overall_result["errors"].append(
                    f"{check_name}: {result.get('error', 'Unknown error')}"
                )

            if result.get("warnings"):
                overall_result["warnings"].extend(result["warnings"])

        overall_result["healthy"] = len(failed_checks) == 0

        if failed_checks:
            logger.error(
                "Startup health checks failed",
                failed_checks=failed_checks,
                errors=overall_result["errors"],
            )
            raise StartupCheckError(
                f"Startup health checks failed: {', '.join(failed_checks)}", failed_checks
            )

        if overall_result["warnings"]:
            logger.warning(
                "Startup health checks completed with warnings", warnings=overall_result["warnings"]
            )
        else:
            logger.info("All startup health checks passed")

        return overall_result

    async def _check_configuration(self) -> Dict[str, Any]:
        """Check configuration validation"""
        try:
            logger.info("Checking configuration validation")

            config_result = validate_environment_variables()

            return {
                "healthy": True,
                "status": "passed",
                "message": "Configuration validation successful",
                "details": config_result,
                "warnings": config_result.get("warnings", []),
            }

        except ConfigurationError as e:
            logger.error("Configuration validation failed", error=str(e))
            return {
                "healthy": False,
                "status": "failed",
                "error": str(e),
                "missing_vars": e.missing_vars,
            }

        except Exception as e:
            logger.error("Unexpected error during configuration check", error=str(e))
            return {
                "healthy": False,
                "status": "error",
                "error": f"Unexpected configuration error: {str(e)}",
            }

    async def _check_supabase_connection(self) -> Dict[str, Any]:
        """Check Supabase database connection"""
        try:
            logger.info("Checking Supabase connection")

            if not settings.NODE_KNOWLEDGE_SUPABASE_URL or not settings.NODE_KNOWLEDGE_SUPABASE_KEY:
                return {
                    "healthy": False,
                    "status": "failed",
                    "error": "Supabase credentials not configured",
                }

            # Create a test client
            supabase = create_client(
                settings.NODE_KNOWLEDGE_SUPABASE_URL, settings.NODE_KNOWLEDGE_SUPABASE_KEY
            )

            # Test connection with a simple query
            response = supabase.table("node_knowledge_vectors").select("id").limit(1).execute()

            logger.info(
                "Supabase connection successful",
                record_count=len(response.data) if response.data else 0,
            )

            return {
                "healthy": True,
                "status": "connected",
                "message": "Supabase connection successful",
                "details": {
                    "url": settings.NODE_KNOWLEDGE_SUPABASE_URL,
                    "test_query_results": len(response.data) if response.data else 0,
                },
            }

        except Exception as e:
            logger.error("Supabase connection failed", error=str(e))
            return {
                "healthy": False,
                "status": "failed",
                "error": f"Supabase connection failed: {str(e)}",
                "details": {
                    "url": settings.NODE_KNOWLEDGE_SUPABASE_URL,
                    "configured": bool(
                        settings.NODE_KNOWLEDGE_SUPABASE_URL
                        and settings.NODE_KNOWLEDGE_SUPABASE_KEY
                    ),
                },
            }

    async def _check_node_knowledge_service(self) -> Dict[str, Any]:
        """Check Node Knowledge service health"""
        try:
            logger.info("Checking Node Knowledge service")

            # Create client and run health check
            NodeKnowledgeClient = get_node_knowledge_client()
            client = NodeKnowledgeClient()
            health_result = client.health_check()

            if health_result.get("healthy"):
                logger.info("Node Knowledge service healthy", details=health_result)
                return {
                    "healthy": True,
                    "status": "healthy",
                    "message": "Node Knowledge service is operational",
                    "details": health_result,
                }
            else:
                logger.error("Node Knowledge service unhealthy", details=health_result)
                return {
                    "healthy": False,
                    "status": "unhealthy",
                    "error": health_result.get("error", "Service health check failed"),
                    "details": health_result,
                }

        except Exception as e:
            logger.error("Node Knowledge service check failed", error=str(e))
            return {
                "healthy": False,
                "status": "error",
                "error": f"Node Knowledge service check failed: {str(e)}",
            }

    def get_check_summary(self) -> Dict[str, Any]:
        """Get a summary of all health check results"""
        return {
            "total_checks": len(self.check_results),
            "passed": sum(1 for result in self.check_results.values() if result.get("healthy")),
            "failed": sum(1 for result in self.check_results.values() if not result.get("healthy")),
            "checks": self.check_results,
        }


async def run_startup_checks() -> Dict[str, Any]:
    """
    Run all startup health checks

    Returns:
        Dict with health check results

    Raises:
        StartupCheckError: If critical checks fail
    """
    checker = StartupHealthChecker()
    return await checker.run_all_checks()


def log_startup_status(check_results: Dict[str, Any]):
    """Log startup status with proper formatting"""
    if check_results.get("healthy"):
        logger.info(
            "🚀 API Gateway startup successful",
            mcp_enabled=settings.MCP_ENABLED,
            checks_passed=len([c for c in check_results["checks"].values() if c.get("healthy")]),
            total_checks=len(check_results["checks"]),
        )
    else:
        logger.error(
            "❌ API Gateway startup failed",
            errors=check_results.get("errors", []),
            failed_checks=len(
                [c for c in check_results["checks"].values() if not c.get("healthy")]
            ),
            total_checks=len(check_results["checks"]),
        )

    # Log individual check results
    for check_name, result in check_results["checks"].items():
        status_emoji = "✅" if result.get("healthy") else "❌"
        if result.get("status") == "skipped":
            status_emoji = "⏭️"

        logger.info(
            f"{status_emoji} {check_name.replace('_', ' ').title()}",
            status=result.get("status"),
            message=result.get("message", result.get("error", "No message")),
        )
