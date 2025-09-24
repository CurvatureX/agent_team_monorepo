"""Test cleanup utilities for maintaining test data isolation."""
import asyncio
from typing import Any, Dict, List, Set


class TestDataCleaner:
    """Utility class for cleaning up test data after test execution."""

    def __init__(self, in_memory_db, in_memory_logs):
        self.db = in_memory_db
        self.logs = in_memory_logs
        self.tracked_executions: Set[str] = set()
        self.tracked_workflows: Set[str] = set()

    def track_execution(self, execution_id: str) -> None:
        """Track an execution ID for cleanup."""
        self.tracked_executions.add(execution_id)

    def track_workflow(self, workflow_id: str) -> None:
        """Track a workflow ID for cleanup."""
        self.tracked_workflows.add(workflow_id)

    async def cleanup_execution(self, execution_id: str) -> bool:
        """Clean up a specific execution and its logs."""
        try:
            # Remove execution from database
            if execution_id in self.db.executions:
                del self.db.executions[execution_id]

            # Remove logs
            if execution_id in self.logs.logs:
                del self.logs.logs[execution_id]

            # Remove from tracking
            self.tracked_executions.discard(execution_id)
            return True
        except Exception:
            return False

    async def cleanup_workflow(self, workflow_id: str) -> bool:
        """Clean up a specific workflow and all its executions."""
        try:
            # Find and clean up all executions for this workflow
            executions_to_remove = []
            for exec_id, exec_data in self.db.executions.items():
                if exec_data.get("workflow_id") == workflow_id:
                    executions_to_remove.append(exec_id)

            for exec_id in executions_to_remove:
                await self.cleanup_execution(exec_id)

            # Remove workflow from database
            if workflow_id in self.db.workflows:
                del self.db.workflows[workflow_id]

            # Remove from tracking
            self.tracked_workflows.discard(workflow_id)
            return True
        except Exception:
            return False

    async def cleanup_all_tracked(self) -> Dict[str, bool]:
        """Clean up all tracked test data."""
        results = {}

        # Clean up tracked executions
        for execution_id in list(self.tracked_executions):
            results[f"execution_{execution_id}"] = await self.cleanup_execution(execution_id)

        # Clean up tracked workflows
        for workflow_id in list(self.tracked_workflows):
            results[f"workflow_{workflow_id}"] = await self.cleanup_workflow(workflow_id)

        return results

    async def verify_cleanup_success(self) -> Dict[str, Any]:
        """Verify that all tracked data has been successfully cleaned up."""
        verification_results = {
            "executions_remaining": [],
            "workflows_remaining": [],
            "logs_remaining": [],
            "cleanup_success": True,
        }

        # Check for remaining executions
        for execution_id in self.tracked_executions:
            if execution_id in self.db.executions:
                verification_results["executions_remaining"].append(execution_id)
                verification_results["cleanup_success"] = False

        # Check for remaining workflows
        for workflow_id in self.tracked_workflows:
            if workflow_id in self.db.workflows:
                verification_results["workflows_remaining"].append(workflow_id)
                verification_results["cleanup_success"] = False

        # Check for remaining logs
        for execution_id in self.tracked_executions:
            if execution_id in self.logs.logs:
                verification_results["logs_remaining"].append(execution_id)
                verification_results["cleanup_success"] = False

        return verification_results

    def reset_tracking(self) -> None:
        """Reset all tracking sets."""
        self.tracked_executions.clear()
        self.tracked_workflows.clear()

    def get_tracked_count(self) -> Dict[str, int]:
        """Get count of tracked items."""
        return {
            "executions": len(self.tracked_executions),
            "workflows": len(self.tracked_workflows),
        }


async def cleanup_test_data(test_context: Dict[str, Any]) -> Dict[str, bool]:
    """Clean up all test data after test completion."""
    cleaner = test_context.get("cleaner")
    if not cleaner:
        return {"error": "No cleaner available in test context"}

    return await cleaner.cleanup_all_tracked()


async def verify_cleanup_success(test_context: Dict[str, Any]) -> Dict[str, Any]:
    """Verify all test data has been removed."""
    cleaner = test_context.get("cleaner")
    if not cleaner:
        return {"error": "No cleaner available in test context"}

    return await cleaner.verify_cleanup_success()


def create_test_cleaner(in_memory_db, in_memory_logs) -> TestDataCleaner:
    """Factory function to create a test data cleaner."""
    return TestDataCleaner(in_memory_db, in_memory_logs)


class TestIsolationManager:
    """Manager for ensuring test isolation and cleanup."""

    def __init__(self):
        self.active_tests: Dict[str, TestDataCleaner] = {}

    def start_test(self, test_name: str, in_memory_db, in_memory_logs) -> TestDataCleaner:
        """Start tracking a new test."""
        cleaner = TestDataCleaner(in_memory_db, in_memory_logs)
        self.active_tests[test_name] = cleaner
        return cleaner

    async def finish_test(self, test_name: str) -> Dict[str, Any]:
        """Finish a test and clean up its data."""
        if test_name not in self.active_tests:
            return {"error": f"Test {test_name} not found"}

        cleaner = self.active_tests[test_name]
        cleanup_results = await cleaner.cleanup_all_tracked()
        verification_results = await cleaner.verify_cleanup_success()

        # Remove from active tests
        del self.active_tests[test_name]

        return {
            "cleanup_results": cleanup_results,
            "verification_results": verification_results,
            "test_completed": True,
        }

    def get_active_test_count(self) -> int:
        """Get count of active tests."""
        return len(self.active_tests)

    async def cleanup_all_tests(self) -> Dict[str, Any]:
        """Clean up all active tests (for teardown)."""
        results = {}
        for test_name in list(self.active_tests.keys()):
            results[test_name] = await self.finish_test(test_name)
        return results


# Global test isolation manager
test_isolation_manager = TestIsolationManager()


async def auto_cleanup_after_test(
    test_name: str, execution_id: str, workflow_id: str = None
) -> None:
    """Automatically clean up after a test execution."""
    if test_name in test_isolation_manager.active_tests:
        cleaner = test_isolation_manager.active_tests[test_name]
        cleaner.track_execution(execution_id)
        if workflow_id:
            cleaner.track_workflow(workflow_id)


def assert_test_isolation_maintained(
    before_state: Dict[str, Any], after_state: Dict[str, Any]
) -> None:
    """Assert that test isolation is maintained between tests."""
    # Check that no data leaked between tests
    before_executions = set(before_state.get("executions", {}).keys())
    after_executions = set(after_state.get("executions", {}).keys())

    leaked_executions = after_executions - before_executions
    assert not leaked_executions, f"Test data leaked between tests: {leaked_executions}"

    before_workflows = set(before_state.get("workflows", {}).keys())
    after_workflows = set(after_state.get("workflows", {}).keys())

    leaked_workflows = after_workflows - before_workflows
    assert not leaked_workflows, f"Workflow data leaked between tests: {leaked_workflows}"


def get_test_state_snapshot(in_memory_db, in_memory_logs) -> Dict[str, Any]:
    """Get a snapshot of current test state for isolation checking."""
    return {
        "executions": dict(in_memory_db.executions),
        "workflows": dict(in_memory_db.workflows),
        "logs": dict(in_memory_logs.logs),
        "timestamp": asyncio.get_event_loop().time(),
    }


class PerformanceTracker:
    """Track performance metrics during test execution."""

    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.start_times: Dict[str, float] = {}

    def start_timer(self, metric_name: str) -> None:
        """Start timing a metric."""
        self.start_times[metric_name] = asyncio.get_event_loop().time()

    def stop_timer(self, metric_name: str) -> float:
        """Stop timing a metric and record the duration."""
        if metric_name not in self.start_times:
            return 0.0

        duration = asyncio.get_event_loop().time() - self.start_times[metric_name]
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(duration)

        del self.start_times[metric_name]
        return duration

    def get_average_time(self, metric_name: str) -> float:
        """Get average time for a metric."""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return 0.0
        return sum(self.metrics[metric_name]) / len(self.metrics[metric_name])

    def get_max_time(self, metric_name: str) -> float:
        """Get maximum time for a metric."""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return 0.0
        return max(self.metrics[metric_name])

    def assert_performance_target(self, metric_name: str, max_duration: float) -> None:
        """Assert that performance targets are met."""
        if metric_name not in self.metrics:
            assert False, f"No performance data for metric '{metric_name}'"

        avg_time = self.get_average_time(metric_name)
        max_time = self.get_max_time(metric_name)

        assert (
            avg_time <= max_duration
        ), f"Average time {avg_time:.2f}s exceeds target {max_duration}s for {metric_name}"
        assert (
            max_time <= max_duration * 2
        ), f"Max time {max_time:.2f}s exceeds tolerance for {metric_name}"
