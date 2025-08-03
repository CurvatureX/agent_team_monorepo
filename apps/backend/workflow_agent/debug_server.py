import uvicorn
from agents.workflow_agent import WorkflowAgent
from dotenv import load_dotenv
from fastapi import FastAPI
import logging
# from langgraph.server import add_routes  # Not available in current LangGraph version

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

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
    logger.error("Failed to initialize and set up the debug server", extra={"error": str(e)})
    # Exit or handle error appropriately
    exit(1)


if __name__ == "__main__":
    logger.info("Starting debug server with uvicorn.")
    uvicorn.run(app, host="0.0.0.0", port=8001)
