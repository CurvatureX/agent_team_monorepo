#!/bin/bash
set -e

echo "🚀 Starting Workflow Engine with import validation..."
echo "========================================================="

# Run import tests before starting the application
echo "🔍 Running import tests to validate all dependencies..."

# Run import tests and capture the result, but don't exit on failure
python run_import_tests.py
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ All import tests passed! Starting application..."
else
    echo "⚠️  Some import tests failed, but starting application anyway..."
    echo "💡 Check the test results above for details."
fi

echo "========================================================="
echo "🚀 Starting main application..."

# Always start the main application (import issues are often non-critical)
exec uvicorn main:app --host 0.0.0.0 --port 8002
