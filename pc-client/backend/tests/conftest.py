import os, sys
import pytest

# Add backend directory to Python path so imports work in CI
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Configure asyncio mode
pytest_plugins = ('pytest_asyncio',)