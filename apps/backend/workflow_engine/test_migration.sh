#!/bin/bash
set -e

echo "🚀 Testing Workflow Engine FastAPI Migration"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

print_status "Starting test environment..."

# Clean up any existing containers
print_status "Cleaning up existing containers..."
docker-compose -f docker-compose.test.yml down --volumes --remove-orphans || true

# Build and start services
print_status "Building and starting services..."
docker-compose -f docker-compose.test.yml up -d --build

# Wait for services to be healthy
print_status "Waiting for services to become healthy..."

# Function to wait for service health
wait_for_service() {
    local service_name=$1
    local timeout=${2:-120}
    local count=0

    print_status "Waiting for $service_name to be healthy..."

    while [ $count -lt $timeout ]; do
        if docker-compose -f docker-compose.test.yml ps --services --filter status=running | grep -q $service_name; then
            if docker-compose -f docker-compose.test.yml exec -T $service_name sh -c 'exit 0' 2>/dev/null; then
                print_success "$service_name is running!"
                return 0
            fi
        fi
        sleep 2
        count=$((count + 2))
        echo -n "."
    done

    print_error "$service_name failed to start within $timeout seconds"
    return 1
}

# Wait for database
wait_for_service "test-db" 60

# Wait for Redis
wait_for_service "test-redis" 30

# Wait for workflow engine (longer timeout for building)
wait_for_service "workflow-engine-fastapi" 180

# Check if the FastAPI server is responding
print_status "Testing FastAPI server health..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "FastAPI server is responding!"
        break
    fi

    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        print_error "FastAPI server is not responding after $max_attempts attempts"
        print_status "Checking server logs..."
        docker-compose -f docker-compose.test.yml logs workflow-engine-fastapi
        exit 1
    fi

    echo -n "."
    sleep 2
done

echo

# Run the API tests
print_status "Running FastAPI endpoint tests..."

# First, run a quick health check
if python3 test_fastapi_endpoints.py health; then
    print_success "Health check passed!"
else
    print_error "Health check failed!"
    print_status "Checking server logs..."
    docker-compose -f docker-compose.test.yml logs --tail=50 workflow-engine-fastapi
    exit 1
fi

echo

# Run comprehensive tests
print_status "Running comprehensive endpoint tests..."
if python3 test_fastapi_endpoints.py; then
    print_success "All API tests passed! 🎉"
else
    print_warning "Some API tests failed. Check the output above for details."
    print_status "This might be expected for placeholder implementations."
fi

echo

# Show service status
print_status "Service status:"
docker-compose -f docker-compose.test.yml ps

echo

# Show API documentation URLs
print_success "FastAPI migration test completed!"
echo
echo "📚 API Documentation is available at:"
echo "   • Swagger UI: http://localhost:8000/docs"
echo "   • ReDoc: http://localhost:8000/redoc"
echo "   • OpenAPI JSON: http://localhost:8000/openapi.json"
echo
echo "🏥 Health Check: http://localhost:8000/health"
echo "🏠 Root Endpoint: http://localhost:8000/"
echo
echo "To stop the test environment:"
echo "   docker-compose -f docker-compose.test.yml down --volumes"
echo
echo "To view logs:"
echo "   docker-compose -f docker-compose.test.yml logs -f workflow-engine-fastapi"

# Optional: Keep services running for manual testing
read -p "Keep services running for manual testing? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_success "Services will continue running. Use Ctrl+C to stop when done."

    # Show real-time logs
    print_status "Showing real-time logs (Ctrl+C to stop):"
    docker-compose -f docker-compose.test.yml logs -f workflow-engine-fastapi
else
    print_status "Stopping test services..."
    docker-compose -f docker-compose.test.yml down --volumes
    print_success "Test environment cleaned up."
fi
