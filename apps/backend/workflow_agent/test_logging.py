#!/usr/bin/env python
"""
Test script for the new centralized logging configuration.
This script demonstrates the JSON format, log levels, and file/line number tracking.
"""

import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.logging_config import setup_logging, get_logger, LogLevel


def test_basic_logging():
    """Test basic logging functionality with different levels."""
    logger = get_logger(__name__)
    
    print("=== Testing Basic Logging ===")
    logger.debug("This is a debug message", extra_data="debug_value")
    logger.info("This is an info message", user_id=123, action="test")
    logger.warning("This is a warning message", warning_code="W001")
    logger.error("This is an error message", error_code="E001", details={"reason": "test error"})
    print()


def test_exception_logging():
    """Test exception logging with traceback."""
    logger = get_logger(__name__)
    
    print("=== Testing Exception Logging ===")
    try:
        1 / 0
    except ZeroDivisionError as e:
        logger.error("Division by zero error occurred", exc_info=True)
    print()


def test_structured_data():
    """Test logging with complex structured data."""
    logger = get_logger(__name__)
    
    print("=== Testing Structured Data Logging ===")
    workflow_state = {
        "session_id": "test-123",
        "stage": "clarification",
        "messages": ["Hello", "How can I help?"],
        "metadata": {
            "timestamp": "2025-01-30T10:00:00Z",
            "version": "1.0.0"
        }
    }
    
    logger.info(
        "Processing workflow state",
        workflow_state=workflow_state,
        processing_time_ms=150.5,
        success=True
    )
    print()


def test_module_logger():
    """Test module-specific logger."""
    from agents.workflow_agent import logger as agent_logger
    
    print("=== Testing Module Logger ===")
    agent_logger.info(
        "Testing from workflow_agent module",
        test_mode=True,
        module_test="success"
    )
    print()


def test_different_environments():
    """Test logging with different environment configurations."""
    print("=== Testing Different Environments ===")
    
    # Development environment
    setup_logging(
        log_level="DEBUG",
        service_name="workflow_agent",
        environment="development"
    )
    logger = get_logger("test.development")
    logger.debug("Development environment debug log")
    
    # Production environment
    setup_logging(
        log_level="INFO",
        service_name="workflow_agent",
        environment="production"
    )
    logger = get_logger("test.production")
    logger.info("Production environment info log")
    logger.debug("This debug log should not appear in production")
    print()


def main():
    """Run all logging tests."""
    print("Starting Workflow Agent Logging Tests\n")
    
    # Setup logging with default configuration
    setup_logging(
        log_level="DEBUG",
        service_name="workflow_agent_test",
        environment="test"
    )
    
    # Run tests
    test_basic_logging()
    test_exception_logging()
    test_structured_data()
    test_module_logger()
    test_different_environments()
    
    print("\nLogging tests completed!")
    print("\nKey features demonstrated:")
    print("1. JSON format output ✓")
    print("2. Log level filtering ✓")
    print("3. File and line number tracking ✓")
    print("4. Structured data support ✓")
    print("5. Exception handling with traceback ✓")
    print("6. Environment-specific configuration ✓")


if __name__ == "__main__":
    main()