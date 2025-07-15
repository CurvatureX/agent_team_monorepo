"""Basic tests to verify project structure."""

import pytest
from workflow_engine import __version__


def test_version():
    """Test that version is properly set."""
    assert __version__ == "0.1.0"


def test_import_modules():
    """Test that all main modules can be imported."""
    # Test core module
    from workflow_engine import core
    assert core is not None
    
    # Test other modules
    from workflow_engine import models
    from workflow_engine import schemas
    from workflow_engine import api
    from workflow_engine import services
    from workflow_engine import nodes
    from workflow_engine import utils
    
    assert models is not None
    assert schemas is not None
    assert api is not None
    assert services is not None
    assert nodes is not None
    assert utils is not None


def test_api_v1_import():
    """Test that API v1 module can be imported."""
    from workflow_engine.api import v1
    assert v1 is not None 