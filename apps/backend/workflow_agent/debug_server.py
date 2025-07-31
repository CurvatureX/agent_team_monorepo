import uvicorn
from agents.workflow_agent import WorkflowAgent
from dotenv import load_dotenv
from fastapi import FastAPI
from core.logging_config import setup_logging, get_logger
# from langgraph.server import add_routes  # Not available in current LangGraph version

# Load environment variables
load_dotenv()

# Configure logging
setup_logging(
    log_level="DEBUG",  # Debug server uses DEBUG level
    service_name="workflow_agent_debug",
    environment="debug"
)

logger = get_logger(__name__)

# Initialize the FastAPI app
app = FastAPI(
    title="Workflow Agent Debug Server",
    version="1.0",
    description="A server to debug the Workflow Agent using LangGraph Studio",
)

# Initialize the WorkflowAgent
try:
    workflow_agent = WorkflowAgent()
    graph = workflow_agent.graph
    logger.info("WorkflowAgent and graph initialized successfully.")

    # Note: add_routes is not available in current LangGraph version
    # For debugging, use the main gRPC server instead
    logger.info("Debug server initialized. Use main gRPC server for actual testing.")

except Exception as e:
    logger.error("Failed to initialize and set up the debug server", error=str(e))
    # Exit or handle error appropriately
    exit(1)


if __name__ == "__main__":
    logger.info("Starting debug server with uvicorn.")
    uvicorn.run(app, host="0.0.0.0", port=8001)
