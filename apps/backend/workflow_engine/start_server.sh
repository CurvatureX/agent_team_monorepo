#!/bin/bash

# Workflow Engine Unified Server Startup Script
# 工作流引擎统一服务器启动脚本

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVER_SCRIPT="server.py"
PID_FILE="workflow_engine.pid"
LOG_FILE="workflow_engine.log"
PORT=50051

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Workflow Engine Server${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to check if server is running
is_server_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to start server
start_server() {
    print_header
    print_status "Starting Workflow Engine Unified Server..."
    
    if is_server_running; then
        print_warning "Server is already running (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    # Check if Python environment is activated
    if [[ "$VIRTUAL_ENV" == "" ]]; then
        print_warning "Virtual environment not detected. Please activate your virtual environment."
        print_status "Example: source .venv/bin/activate"
        return 1
    fi
    
    # Check if required files exist
    if [ ! -f "$SERVER_SCRIPT" ]; then
        print_error "Server script not found: $SERVER_SCRIPT"
        return 1
    fi
    
    # Generate protobuf files
    print_status "Generating protobuf files..."
    python generate_proto.py
    
    # Start server in background
    print_status "Starting server on port $PORT..."
    nohup python "$SERVER_SCRIPT" > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    # Save PID
    echo $pid > "$PID_FILE"
    
    # Wait a moment for server to start
    sleep 3
    
    # Check if server started successfully
    if is_server_running; then
        print_status "✅ Server started successfully!"
        print_status "📊 PID: $pid"
        print_status "📝 Log file: $LOG_FILE"
        print_status "🌐 Server URL: localhost:$PORT"
        print_status "🔍 Health check: curl http://localhost:$PORT/health"
    else
        print_error "❌ Server failed to start"
        print_status "Check log file: $LOG_FILE"
        return 1
    fi
}

# Function to stop server
stop_server() {
    print_header
    print_status "Stopping Workflow Engine Server..."
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            print_status "Stopping server (PID: $pid)..."
            kill "$pid"
            
            # Wait for server to stop
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            if ps -p "$pid" > /dev/null 2>&1; then
                print_warning "Server did not stop gracefully, forcing termination..."
                kill -9 "$pid"
            fi
            
            rm -f "$PID_FILE"
            print_status "✅ Server stopped"
        else
            print_warning "Server is not running"
            rm -f "$PID_FILE"
        fi
    else
        print_warning "PID file not found, server may not be running"
    fi
}

# Function to restart server
restart_server() {
    print_header
    print_status "Restarting Workflow Engine Server..."
    stop_server
    sleep 2
    start_server
}

# Function to show server status
show_status() {
    print_header
    
    if is_server_running; then
        local pid=$(cat "$PID_FILE")
        print_status "✅ Server is running"
        print_status "📊 PID: $pid"
        print_status "🌐 Port: $PORT"
        print_status "📝 Log file: $LOG_FILE"
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            print_status "Recent log entries:"
            tail -n 10 "$LOG_FILE"
        fi
    else
        print_warning "❌ Server is not running"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_status "Showing server logs:"
        tail -f "$LOG_FILE"
    else
        print_warning "Log file not found: $LOG_FILE"
    fi
}

# Function to test server
test_server() {
    print_header
    print_status "Testing server connection..."
    
    if ! is_server_running; then
        print_error "Server is not running"
        return 1
    fi
    
    # Test basic connectivity
    if command -v curl > /dev/null 2>&1; then
        print_status "Testing HTTP health check..."
        curl -s "http://localhost:$PORT/health" || print_warning "HTTP health check failed"
    fi
    
    # Test gRPC health check
    print_status "Testing gRPC health check..."
    python -c "
import grpc
from grpc_health.v1 import health_pb2_grpc, health_pb2

try:
    channel = grpc.insecure_channel('localhost:$PORT')
    stub = health_pb2_grpc.HealthStub(channel)
    response = stub.Check(health_pb2.HealthCheckRequest())
    print(f'✅ gRPC health check: {response.status}')
except Exception as e:
    print(f'❌ gRPC health check failed: {e}')
"
}

# Function to show help
show_help() {
    print_header
    echo "Usage: $0 {start|stop|restart|status|logs|test|help}"
    echo ""
    echo "Commands:"
    echo "  start     - Start the workflow engine server"
    echo "  stop      - Stop the workflow engine server"
    echo "  restart   - Restart the workflow engine server"
    echo "  status    - Show server status"
    echo "  logs      - Show server logs (follow mode)"
    echo "  test      - Test server connectivity"
    echo "  help      - Show this help message"
    echo ""
    echo "Files:"
    echo "  PID file: $PID_FILE"
    echo "  Log file: $LOG_FILE"
    echo "  Server script: $SERVER_SCRIPT"
}

# Main script logic
case "$1" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    test)
        test_server
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 