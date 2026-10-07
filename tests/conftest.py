"""Pytest configuration ensuring tests run hermetically against Mock sandbox."""

import os
import pytest

@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    os.environ["INBOXGPT_FORCE_MOCK"] = "true"
