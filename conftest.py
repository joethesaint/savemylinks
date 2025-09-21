"""
Pytest configuration for the entire project.
"""

import pytest

pytest_plugins = ('pytest_asyncio',)

# Configure pytest markers for better test organization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )

# Skip slow tests by default in development
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle slow tests."""
    if config.getoption("-m") is None and not config.getoption("--collect-only"):
        # If no marker specified, skip slow tests by default
        skip_slow = pytest.mark.skip(reason="Slow test skipped by default. Use -m slow to run.")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)