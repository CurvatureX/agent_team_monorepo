"""
Workflow Engine package initialization.
Configures import paths to access shared modules.
"""

import os
import sys

# Add parent directory to path to access shared module
parent_dir = os.path.join(os.path.dirname(__file__), "..")
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
