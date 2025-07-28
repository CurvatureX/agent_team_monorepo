"""
Mock gRPC client for development and testing.

Provides a fallback implementation when the actual gRPC workflow service
is unavailable, with configurable responses for testing different scenarios.
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger(__name__)


class MockResponse:
    """Mock response object that mimics gRPC response structure."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        attrs = {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
        return f"MockResponse({attrs})"


class MockWorkflowGRPCClient:
    """
    Mock gRPC client for development and testing.

    Features:
    - Configurable response patterns
    - Simulated latency and errors
    - Different scenario modes (success, failure, timeout)
    - Statistics tracking for testing
    """

    def __init__(self, scenario: str = "success"):
        self.scenario = scenario
        self.connected = True
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "last_request_time": None,
        }

        # Mock configuration
        self.mock_config = {
            "base_delay": 0.1,  # Base response delay in seconds
            "max_delay": 2.0,  # Maximum response delay
            "error_rate": 0.0,  # Error rate (0.0 to 1.0)
            "timeout_rate": 0.0,  # Timeout rate (0.0 to 1.0)
            "response_count": 3,  # Number of streaming responses
        }

        # Scenario-specific configurations
        self._configure_scenario(scenario)

    def _configure_scenario(self, scenario: str):
        """Configure mock behavior based on scenario."""
        if scenario == "success":
            self.mock_config.update(
                {"error_rate": 0.0, "timeout_rate": 0.0, "base_delay": 0.1, "response_count": 3}
            )
        elif scenario == "slow":
            self.mock_config.update(
                {
                    "error_rate": 0.0,
                    "timeout_rate": 0.0,
                    "base_delay": 1.0,
                    "max_delay": 3.0,
                    "response_count": 5,
                }
            )
        elif scenario == "unstable":
            self.mock_config.update(
                {"error_rate": 0.3, "timeout_rate": 0.1, "base_delay": 0.2, "response_count": 2}
            )
        elif scenario == "failure":
            self.mock_config.update({"error_rate": 1.0, "timeout_rate": 0.0, "response_count": 0})
        elif scenario == "timeout":
            self.mock_config.update({"error_rate": 0.0, "timeout_rate": 1.0, "response_count": 0})

        logger.info(f"🎭 Mock client configured for scenario: {scenario}")

    async def connect(self) -> bool:
        """Mock connection - always succeeds unless in 'failure' scenario."""
        await asyncio.sleep(0.1)  # Simulate connection time

        if self.scenario == "failure":
            self.connected = False
            logger.warning("🎭 Mock connection failed (failure scenario)")
            return False

        self.connected = True
        logger.info("🎭 Mock client connected successfully")
        return True

    async def disconnect(self):
        """Mock disconnection."""
        self.connected = False
        logger.info("🎭 Mock client disconnected")

    async def ensure_connected(self) -> bool:
        """Ensure mock connection is available."""
        if not self.connected:
            return await self.connect()
        return True

    async def process_conversation(
        self, request: Any, timeout: float = 60.0
    ) -> AsyncGenerator[MockResponse, None]:
        """
        Mock conversation processing with configurable responses.

        Simulates various scenarios based on configuration:
        - Success: Returns multiple streaming responses
        - Slow: Introduces delays between responses
        - Unstable: Random errors and timeouts
        - Failure: Always fails
        - Timeout: Simulates timeout scenarios
        """
        start_time = time.time()
        self.stats["total_requests"] += 1
        self.stats["last_request_time"] = datetime.utcnow().isoformat()

        try:
            # Check if we should simulate an error
            if random.random() < self.mock_config["error_rate"]:
                self.stats["failed_requests"] += 1
                raise Exception("🎭 Mock gRPC error (simulated)")

            # Check if we should simulate a timeout
            if random.random() < self.mock_config["timeout_rate"]:
                self.stats["failed_requests"] += 1
                await asyncio.sleep(timeout + 1)  # Exceed timeout
                raise asyncio.TimeoutError("🎭 Mock timeout (simulated)")

            # Generate streaming responses
            response_count = self.mock_config["response_count"]

            for i in range(response_count):
                # Simulate processing delay
                delay = random.uniform(
                    self.mock_config["base_delay"],
                    self.mock_config.get("max_delay", self.mock_config["base_delay"] * 2),
                )
                await asyncio.sleep(delay)

                # Create mock response
                response = self._create_mock_response(request, i, response_count)

                logger.debug(f"🎭 Mock response {i+1}/{response_count}: {response}")
                yield response

            # Update success statistics
            self.stats["successful_requests"] += 1
            response_time = time.time() - start_time
            self._update_avg_response_time(response_time)

            logger.info(f"🎭 Mock conversation completed successfully ({response_time:.2f}s)")

        except Exception as e:
            response_time = time.time() - start_time
            self._update_avg_response_time(response_time)
            logger.error(f"🎭 Mock conversation failed: {e}")
            raise

    def _create_mock_response(self, request: Any, index: int, total: int) -> MockResponse:
        """Create a mock response based on the request."""
        # Extract session_id and user_message if available
        session_id = getattr(request, "session_id", "mock-session-123")
        user_message = getattr(request, "user_message", "Hello, mock agent!")

        # Generate different types of responses
        if index == 0:
            # First response: Acknowledgment
            return MockResponse(
                session_id=session_id,
                response_type="acknowledgment",
                message="I understand your request. Let me think about this...",
                status="processing",
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "mock_client": True,
                    "scenario": self.scenario,
                },
            )
        elif index == total - 1:
            # Last response: Final answer
            return MockResponse(
                session_id=session_id,
                response_type="final_response",
                message=f"Mock response to: '{user_message}'. This is a simulated workflow execution result.",
                status="completed",
                workflow_result={
                    "success": True,
                    "steps_executed": 3,
                    "execution_time": f"{random.uniform(0.5, 2.0):.2f}s",
                    "mock_data": {
                        "processed_request": user_message,
                        "scenario": self.scenario,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                },
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "mock_client": True,
                    "scenario": self.scenario,
                },
            )
        else:
            # Intermediate responses: Progress updates
            return MockResponse(
                session_id=session_id,
                response_type="progress_update",
                message=f"Processing step {index}/{total-1}...",
                status="in_progress",
                progress={
                    "current_step": index,
                    "total_steps": total - 1,
                    "completion_percentage": round((index / (total - 1)) * 100, 1),
                },
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "mock_client": True,
                    "scenario": self.scenario,
                },
            )

    def _update_avg_response_time(self, response_time: float):
        """Update average response time statistics."""
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["avg_response_time"]

        # Calculate new average
        self.stats["avg_response_time"] = (
            current_avg * (total_requests - 1) + response_time
        ) / total_requests

    def get_client_stats(self) -> Dict[str, Any]:
        """Get mock client statistics."""
        success_rate = 0.0
        if self.stats["total_requests"] > 0:
            success_rate = (self.stats["successful_requests"] / self.stats["total_requests"]) * 100

        return {
            "client_type": "mock",
            "scenario": self.scenario,
            "client_stats": self.stats,
            "success_rate_percent": round(success_rate, 2),
            "mock_config": self.mock_config,
            "connected": self.connected,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "healthy": self.connected and self.scenario != "failure",
            "client_type": "mock",
            "scenario": self.scenario,
            "connection_status": self.connected,
            "stats": self.get_client_stats(),
        }

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0.0,
            "last_request_time": None,
        }
        logger.info("🎭 Mock client statistics reset")


class MockGRPCClientManager:
    """Manager for mock gRPC client instances."""

    _instances: Dict[str, MockWorkflowGRPCClient] = {}

    @classmethod
    def get_client(cls, scenario: str = "success") -> MockWorkflowGRPCClient:
        """Get or create a mock client for the specified scenario."""
        if scenario not in cls._instances:
            cls._instances[scenario] = MockWorkflowGRPCClient(scenario)
        return cls._instances[scenario]

    @classmethod
    async def close_all(cls):
        """Close all mock client instances."""
        for client in cls._instances.values():
            await client.disconnect()
        cls._instances.clear()
        logger.info("🎭 All mock clients closed")

    @classmethod
    def get_available_scenarios(cls) -> List[str]:
        """Get list of available mock scenarios."""
        return ["success", "slow", "unstable", "failure", "timeout"]


# Convenience functions for testing
async def get_mock_workflow_client(scenario: str = "success") -> MockWorkflowGRPCClient:
    """Get a mock workflow client for testing."""
    client = MockGRPCClientManager.get_client(scenario)
    await client.connect()
    return client


async def test_mock_client(scenario: str = "success", message: str = "Test message"):
    """Test function to demonstrate mock client usage."""
    logger.info(f"🧪 Testing mock client with scenario: {scenario}")

    try:
        # Get mock client
        client = await get_mock_workflow_client(scenario)

        # Create mock request
        mock_request = MockResponse(session_id="test-session-456", user_message=message)

        # Process conversation
        responses = []
        async for response in client.process_conversation(mock_request):
            responses.append(response)
            logger.info(f"📨 Received: {response}")

        # Print statistics
        stats = client.get_client_stats()
        logger.info(f"📊 Client stats: {json.dumps(stats, indent=2, default=str)}")

        return responses

    except Exception as e:
        logger.error(f"❌ Mock client test failed: {e}")
        raise
    finally:
        await MockGRPCClientManager.close_all()


# Example usage
if __name__ == "__main__":

    async def main():
        """Demo the mock client with different scenarios."""
        scenarios = ["success", "slow", "unstable"]

        for scenario in scenarios:
            logger.info(f"\n{'='*50}")
            logger.info(f"Testing scenario: {scenario}")
            logger.info(f"{'='*50}")

            try:
                await test_mock_client(scenario, f"Test message for {scenario} scenario")
            except Exception as e:
                logger.error(f"Scenario {scenario} failed: {e}")

            # Small delay between scenarios
            await asyncio.sleep(1)

    # Configure logging for demo
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main())


# Export commonly used items
__all__ = [
    "MockWorkflowGRPCClient",
    "MockGRPCClientManager",
    "MockResponse",
    "get_mock_workflow_client",
    "test_mock_client",
]
