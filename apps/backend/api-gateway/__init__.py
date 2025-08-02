# API Gateway package
import os
import sys

# Add shared module to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
shared_path = os.path.join(backend_dir, "shared")
if shared_path not in sys.path:
    sys.path.insert(0, shared_path)
