import structlog
import uvicorn
from agents.workflow_agent import WorkflowAgent
from dotenv import load_dotenv
from fastapi import FastAPI
from langgraph.server import add_routes

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

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

    # Add LangGraph routes
    add_routes(
        app,
        graph,
        path="/workflow",
        config_keys=["configurable"],
    )
    logger.info("LangGraph routes added to FastAPI app.")

except Exception as e:
    logger.error("Failed to initialize and set up the debug server", error=str(e))
    # Exit or handle error appropriately
    exit(1)


if __name__ == "__main__":
    logger.info("Starting debug server with uvicorn.")
    uvicorn.run(app, host="0.0.0.0", port=8001)
