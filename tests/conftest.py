"""Shared pytest setup for every test under tests/ (B1).

Loads the verification plugin (hooks and fixtures) and the shared database
fixture. Hooks and fixtures are picked up by name from this module.
"""

from tests.support.db import rubrica_db  # noqa: F401
from tests.verification.plugin import (  # noqa: F401
    agent_token,
    api_client_factory,
    evidence,
    fake_llm,
    live_only,
    mailpit,
    observed,
    pytest_addoption,
    pytest_collection_modifyitems,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_sessionfinish,
)
