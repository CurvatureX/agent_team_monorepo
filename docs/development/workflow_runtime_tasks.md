# Workflow Runtime Development Tasks

Based on [workflow-runtime-architecture.md](../tech-design/workflow-runtime-architecture.md), here are the detailed development tasks for implementing workflow_runtime service.

## Project Overview

**Goal**: Implement workflow_runtime service for Workflow deployment, scheduling, and execution coordination.

**Core Features**:
- Workflow deployment management
- Cron scheduling with hash jitter
- Webhook HTTP triggers (via API Gateway)
- Execution status monitoring
- Distributed locking to prevent duplicate execution

**Important**: All external API access is managed through `apps/backend/api-gateway`. workflow_runtime only provides internal gRPC interfaces.

---

## Phase 1: Infrastructure Setup

### Task 1.1: Project Initialization and Configuration
**Goal**: Create workflow_runtime project foundation

**Tasks**:
- Create `apps/backend/workflow_runtime/` directory structure
- Configure Python project dependencies using uv (pyproject.toml)
- Setup configuration management (settings.py)
- Configure logging system
- Setup environment variable management

**Dependencies**:
```
fastapi >= 0.104.0
uvicorn >= 0.24.0
grpcio >= 1.59.0
grpcio-tools >= 1.59.0
apscheduler >= 3.10.4
redis >= 5.0.0
psycopg2-binary >= 2.9.7
pydantic >= 2.4.0
sqlalchemy >= 2.0.0
alembic >= 1.12.0
```

**Acceptance Criteria**:
- [ ] Project starts successfully
- [ ] Configuration files load correctly
- [ ] Logging outputs structured JSON format
- [ ] Can connect to PostgreSQL and Redis
- [ ] Unit tests run with `make test-runtime`

**Estimated Time**: 0.5 day

---

### Task 1.2: Database Model Extension
**Goal**: Extend existing database tables to support deployment features

**Tasks**:
- Add deployment-related fields to `workflows` table
- Create database migration scripts
- Implement SQLAlchemy model classes
- Add relevant indexes for optimization

**Implementation**:
```sql
-- New fields
ALTER TABLE workflows ADD COLUMN deployment_status VARCHAR(50) DEFAULT 'DRAFT';
ALTER TABLE workflows ADD COLUMN deployed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE workflows ADD COLUMN deployment_config JSONB DEFAULT '{}';

-- Constraints and indexes
ALTER TABLE workflows ADD CONSTRAINT valid_deployment_status
  CHECK (deployment_status IN ('DRAFT', 'DEPLOYED', 'PAUSED', 'ARCHIVED'));
CREATE INDEX idx_workflows_deployment_status ON workflows(deployment_status);
CREATE INDEX idx_workflows_deployed_at ON workflows(deployed_at);
```

**Acceptance Criteria**:
- [ ] Database migration executes successfully
- [ ] SQLAlchemy models correctly map new fields
- [ ] Can query and update deployment status
- [ ] Indexes created successfully with expected performance
- [ ] Data model unit tests pass

**Estimated Time**: 0.5 day

---

### Task 1.3: Redis Connection and Data Structures
**Goal**: Implement Redis connection management and basic data structures

**Tasks**:
- Configure Redis connection pool
- Implement distributed lock manager
- Implement basic data structure operations
- Add Redis health check

**Core Classes**:
```python
class RedisManager:
    def __init__(self, redis_url: str)
    async def get_connection(self) -> Redis
    async def health_check(self) -> bool

class DistributedLockManager:
    async def acquire_lock(self, workflow_id: str, ttl: int = 300) -> bool
    async def release_lock(self, workflow_id: str) -> bool
    async def extend_lock(self, workflow_id: str, ttl: int = 300) -> bool
```

**Acceptance Criteria**:
- [ ] Redis connection pool works properly
- [ ] Distributed lock can be acquired and released correctly
- [ ] Lock timeout mechanism works
- [ ] Lock renewal functionality supported
- [ ] Redis operation error handling is comprehensive
- [ ] Redis operation unit tests pass

**Estimated Time**: 0.5 day

---

## Phase 2: Core Service Implementation

### Task 2.1: Internal gRPC Service Implementation
**Goal**: Implement workflow_runtime internal gRPC API (for API Gateway consumption)

**Tasks**:
- Define gRPC protobuf files for internal interfaces
- Implement DeploymentService gRPC service
- Implement MonitoringService gRPC service
- Add request validation and error handling

**Key Internal Interfaces**:
```protobuf
service WorkflowRuntimeService {
    // Deployment management (called by API Gateway)
    rpc DeployWorkflow(DeployWorkflowRequest) returns (DeployWorkflowResponse);
    rpc UpdateDeployment(UpdateDeploymentRequest) returns (UpdateDeploymentResponse);
    rpc DeleteDeployment(DeleteDeploymentRequest) returns (DeleteDeploymentResponse);
    rpc GetDeploymentStatus(GetDeploymentStatusRequest) returns (GetDeploymentStatusResponse);
    rpc ListDeployments(ListDeploymentsRequest) returns (ListDeploymentsResponse);

    // Monitoring (called by API Gateway)
    rpc GetExecutionHistory(GetExecutionHistoryRequest) returns (GetExecutionHistoryResponse);

    // Webhook trigger (called by API Gateway)
    rpc TriggerWorkflow(TriggerWorkflowRequest) returns (TriggerWorkflowResponse);
}
```

**Acceptance Criteria**:
- [ ] Internal gRPC service starts and listens successfully
- [ ] All interfaces can be called from API Gateway
- [ ] Request parameter validation works
- [ ] Error response format is consistent
- [ ] gRPC reflection is supported for debugging
- [ ] Integration tests with API Gateway pass

**Estimated Time**: 1 day

---

### Task 2.2: Deployment Service Implementation
**Goal**: Implement Workflow deployment lifecycle management

**Tasks**:
- Implement `DeploymentService` class
- Workflow definition validation logic
- Deployment status management
- Trigger configuration processing

**Core Functions**:
```python
class DeploymentService:
    async def deploy_workflow(self, workflow_def: dict, triggers: List[dict]) -> str
    async def update_deployment(self, deployment_id: str, **kwargs) -> bool
    async def delete_deployment(self, deployment_id: str) -> bool
    async def get_deployment_status(self, deployment_id: str) -> dict
    async def list_deployments(self, filters: dict) -> List[dict]

    def _validate_workflow_definition(self, workflow_def: dict) -> bool
    def _validate_triggers(self, triggers: List[dict]) -> bool
```

**Acceptance Criteria**:
- [ ] Can successfully deploy Workflow
- [ ] Workflow definition validation works correctly
- [ ] Trigger configuration validation works correctly
- [ ] Deployment status updates correctly to database
- [ ] Supports deployment pause/resume/delete
- [ ] Exception rollback mechanism works
- [ ] Deployment service integration tests pass

**Estimated Time**: 1 day

---

### Task 2.3: Hash Jitter Scheduler Implementation
**Goal**: Implement hash-based Cron job distribution scheduling

**Tasks**:
- Implement hash jitter algorithm
- Integrate APScheduler for Cron scheduling
- Implement scheduler lifecycle management
- Add scheduling monitoring and logging

**Core Implementation**:
```python
def calculate_jitter(workflow_id: str, time_window: int = 300) -> int:
    """Calculate fixed delay based on workflow_id"""
    import hashlib
    hash_value = hashlib.md5(workflow_id.encode()).hexdigest()
    jitter_seconds = int(hash_value[:8], 16) % time_window
    return jitter_seconds

class CronScheduler:
    def __init__(self, scheduler: AsyncIOScheduler)
    async def schedule_workflow(self, workflow_id: str, cron_expression: str)
    async def unschedule_workflow(self, workflow_id: str)
    async def execute_with_jitter(self, workflow_id: str)
```

**Acceptance Criteria**:
- [ ] Hash jitter algorithm implemented correctly
- [ ] Same workflow_id has fixed delay
- [ ] Cron scheduling works correctly
- [ ] Tasks are distributed within 5-minute window
- [ ] Scheduler supports start/stop/restart
- [ ] Scheduling execution logs are recorded
- [ ] Scheduler unit and integration tests pass

**Estimated Time**: 0.5 day

---

### Task 2.4: API Gateway Integration Implementation
**Goal**: Implement workflow_runtime integration with API Gateway

**Tasks**:
- Design Webhook trigger gRPC interface for API Gateway
- Implement webhook registration and management
- Create API Gateway client interface for workflow_runtime
- Integration with execution coordinator

**Core Implementation**:
```python
class WebhookTriggerService:
    """Handles webhook triggers from API Gateway via gRPC"""

    async def register_webhook_deployment(self, workflow_id: str, webhook_config: dict) -> str
    async def unregister_webhook_deployment(self, workflow_id: str) -> bool
    async def handle_webhook_trigger(self, workflow_id: str, webhook_data: dict) -> dict

    def _validate_webhook_config(self, webhook_config: dict) -> bool
    def _lookup_workflow_by_webhook_path(self, webhook_path: str) -> str

# gRPC service method for API Gateway
async def TriggerWorkflow(self, request, context):
    """Called by API Gateway when webhook is received"""
    workflow_id = request.workflow_id
    webhook_data = json.loads(request.trigger_data)
    return await self.webhook_service.handle_webhook_trigger(workflow_id, webhook_data)
```

**API Gateway Integration Points**:
- API Gateway manages webhook HTTP endpoints
- API Gateway validates webhook signatures and extracts data
- API Gateway calls workflow_runtime gRPC to trigger execution
- workflow_runtime returns execution status to API Gateway

**Acceptance Criteria**:
- [ ] Webhook registration via gRPC interface works
- [ ] API Gateway can successfully trigger workflow execution
- [ ] Webhook path lookup and validation works
- [ ] Request data parsed and passed correctly via gRPC
- [ ] Error handling between API Gateway and workflow_runtime
- [ ] Integration tests with API Gateway pass

**Estimated Time**: 0.5 day

---

### Task 2.5: Execution Coordinator Service Implementation
**Goal**: Implement Workflow execution coordination and status management

**Tasks**:
- Implement `ExecutionCoordinatorService` class
- gRPC communication with workflow_engine
- Execution status tracking and updates
- Distributed lock integration

**Core Functions**:
```python
class ExecutionCoordinatorService:
    def __init__(self, engine_client: WorkflowEngineClient, lock_manager: DistributedLockManager)

    async def trigger_execution(self, workflow_id: str, trigger_data: dict) -> str
    async def get_execution_status(self, execution_id: str) -> dict
    async def cancel_execution(self, execution_id: str) -> bool

    async def _execute_workflow_with_lock(self, workflow_id: str, input_data: dict) -> dict
    async def _update_execution_status(self, execution_id: str, status: str, result_data: dict = None)
```

**Acceptance Criteria**:
- [ ] Successfully calls workflow_engine gRPC interface
- [ ] Distributed lock prevents duplicate execution
- [ ] Execution status recorded correctly to database
- [ ] Supports execution cancellation
- [ ] Exception scenarios handled and recorded correctly
- [ ] Execution timeout detection and handling
- [ ] Execution coordination integration tests pass

**Estimated Time**: 0.5 day

---

## Phase 3: Monitoring and Operations

### Task 3.1: Monitoring Service Implementation
**Goal**: Implement system monitoring and metrics collection

**Tasks**:
- Implement `MonitoringService` class
- Deployment status statistics
- Execution history queries
- System health checks

**Core Functions**:
```python
class MonitoringService:
    async def get_deployment_stats(self) -> dict
    async def get_execution_history(self, filters: dict) -> List[dict]
    async def get_system_health(self) -> dict
    async def get_scheduling_metrics(self) -> dict

    # Hash jitter monitoring metrics
    async def get_jitter_distribution(self) -> dict
    async def get_load_distribution(self) -> dict
```

**Acceptance Criteria**:
- [ ] Correctly calculates deployment status distribution
- [ ] Execution history query functionality works
- [ ] System health status check is accurate
- [ ] Hash jitter effect monitoring works correctly
- [ ] Monitoring data format is standardized
- [ ] Supports time range filtering
- [ ] Monitoring service tests pass

**Estimated Time**: 0.5 day

---

### Task 3.2: Logging and Error Handling
**Goal**: Improve logging and error handling mechanisms

**Tasks**:
- Standardize log format and levels
- Structured logging output (JSON)
- Error classification and handling strategies
- Request tracing

**Implementation Points**:
```python
import structlog

logger = structlog.get_logger()

# Standardized log format
logger.info("workflow_deployed",
    workflow_id=workflow_id,
    deployment_id=deployment_id,
    user_id=user_id,
    trigger_count=len(triggers)
)

# Error handling
class WorkflowRuntimeError(Exception):
    pass

class DeploymentValidationError(WorkflowRuntimeError):
    pass
```

**Acceptance Criteria**:
- [ ] Log output is structured JSON format
- [ ] Contains request trace_id for tracing
- [ ] Error classification is clear for easy troubleshooting
- [ ] Sensitive information is properly masked
- [ ] Log level configuration is flexible
- [ ] Supports log rotation and archiving
- [ ] Log format validation passes

**Estimated Time**: 0.5 day

---

### Task 3.3: Health Check and Graceful Shutdown
**Goal**: Implement service health check and graceful shutdown mechanism

**Tasks**:
- Implement health check endpoint
- Dependency service status checks
- Graceful shutdown process
- Signal handling

**Implementation Points**:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": __version__,
        "dependencies": {
            "database": await check_database_health(),
            "redis": await check_redis_health(),
            "workflow_engine": await check_engine_health()
        }
    }

async def graceful_shutdown():
    # Stop accepting new requests
    # Wait for current executions to complete
    # Clean up resources
```

**Acceptance Criteria**:
- [ ] `/health` endpoint returns service status
- [ ] Dependency service health checks work correctly
- [ ] Supports graceful shutdown without interrupting running tasks
- [ ] SIGTERM signal handled correctly
- [ ] Resource cleanup is complete
- [ ] Shutdown process logs are clear
- [ ] Health check and shutdown process tests pass

**Estimated Time**: 0.5 day

---

## Phase 4: Testing and Deployment

### Task 4.1: Unit Tests
**Goal**: Implement comprehensive unit test coverage

**Tasks**:
- Core service class unit tests
- Hash jitter algorithm tests
- Redis operation tests
- Database operation tests
- Mock dependency services

**Test Coverage**:
- DeploymentService method tests
- CronScheduler scheduling logic tests
- ExecutionCoordinatorService execution flow tests
- WebhookService request processing tests
- DistributedLockManager lock operation tests

**Acceptance Criteria**:
- [ ] Code coverage >= 85%
- [ ] All core functions have corresponding tests
- [ ] Test cases cover normal and exception scenarios
- [ ] External dependencies mocked correctly
- [ ] Test execution time < 30 seconds
- [ ] Tests run with `make test-runtime`

**Estimated Time**: 0.5 day

---

### Task 4.2: Integration Tests
**Goal**: Verify service integration and end-to-end flows

**Tasks**:
- Docker Compose test environment
- gRPC client integration tests
- Webhook end-to-end tests
- Integration tests with workflow_engine
- Multi-instance deployment tests

**Test Scenarios**:
- Deploy -> Trigger -> Execute -> Monitor complete flow
- Cron scheduled trigger tests
- Webhook HTTP trigger tests
- Distributed lock concurrent tests
- Failure recovery tests

**Acceptance Criteria**:
- [ ] Docker environment starts all dependencies normally
- [ ] End-to-end flow tests pass
- [ ] Hash jitter effect validation correct
- [ ] Concurrent execution tests have no conflicts
- [ ] Failure scenarios recover normally
- [ ] Performance tests meet requirements (QPS >= 100)
- [ ] Tests run with `make test-integration-runtime`

**Estimated Time**: 0.5 day

---

### Task 4.3: Deployment Configuration and Documentation
**Goal**: Prepare production deployment configuration and usage documentation

**Tasks**:
- Docker image build configuration
- Kubernetes deployment YAML
- Environment variable configuration documentation
- Operations documentation
- API usage examples

**Deliverables**:
- `Dockerfile` and `.dockerignore`
- `k8s/` directory containing all K8s resource files
- `docs/deployment/workflow-runtime.md` deployment documentation
- `docs/api/workflow-runtime-api.md` API documentation
- `examples/` directory containing usage examples

**Acceptance Criteria**:
- [ ] Docker image builds successfully
- [ ] K8s deployment configuration is correct
- [ ] Environment variable documentation is complete
- [ ] API documentation includes all interface descriptions
- [ ] Usage examples run normally
- [ ] Deployment documentation steps are clear
- [ ] Service can be successfully deployed following documentation

**Estimated Time**: 0.5 day

---

## Overall Time Estimation

| Phase | Task Count | Estimated Time |
|-------|------------|----------------|
| Phase 1: Infrastructure | 3 tasks | 1.5 days |
| Phase 2: Core Services | 5 tasks | 3.5 days |
| Phase 3: Monitoring Ops | 3 tasks | 1.5 days |
| Phase 4: Testing Deployment | 3 tasks | 1.5 days |
| **Total** | **14 tasks** | **7.5 days** |

## Milestone Checkpoints

### 🎯 Milestone 1: Infrastructure Ready (Day 2)
- [ ] Project can start, connects to database and Redis
- [ ] Database model extension complete
- [ ] Distributed lock works normally

### 🎯 Milestone 2: Core Features Complete (Day 5)
- [ ] gRPC API can be called normally
- [ ] Workflow deployment functionality works
- [ ] Cron and Webhook triggers work normally
- [ ] Execution coordination functionality works

### 🎯 Milestone 3: Monitoring Operations Complete (Day 6.5)
- [ ] Monitoring metrics collected normally
- [ ] Logging and error handling improved
- [ ] Health check works normally

### 🎯 Milestone 4: Production Ready (Day 7.5)
- [ ] All tests pass
- [ ] Deployment configuration and documentation complete
- [ ] Can be deployed and run in production environment

## Development Recommendations

1. **Parallel Development**: After Phase 1, multiple tasks in Phase 2 can be done in parallel
2. **Iterative Validation**: Perform functional validation after each Milestone
3. **Early Integration**: Integrate with workflow_engine as early as possible
4. **Performance Testing**: Continuously perform performance testing during development
5. **Code Review**: Conduct code review after each task completion

## Risk Identification

| Risk Item | Impact | Mitigation Strategy |
|-----------|--------|-------------------|
| workflow_engine API changes | High | Early integration testing, communicate with engine team |
| Distributed lock performance issues | Medium | Stress testing, Redis configuration optimization |
| Hash jitter effect not ideal | Medium | Algorithm validation, monitoring data verification |
| gRPC service stability | Medium | Improve exception handling, retry mechanism |
| Database performance bottleneck | Medium | Index optimization, query performance testing |
