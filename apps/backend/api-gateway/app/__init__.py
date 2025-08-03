# API Gateway MVP Package
import os
import sys

# Setup shared module path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "../.."))
shared_path = os.path.join(backend_dir, "shared")

if os.path.exists(shared_path) and shared_path not in sys.path:
    sys.path.insert(0, shared_path)