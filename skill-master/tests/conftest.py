"""Shared pytest configuration for the skill-master test suite."""

import pytest


def pytest_sessionfinish(session: pytest.Session, exitstatus: int | pytest.ExitCode) -> None:
    """Treat an empty test suite (exit code 5, NO_TESTS_COLLECTED) as success.

    The project starts with a pytest baseline and zero tests; without this,
    a bare ``uv run pytest`` fails CI. Remove once real tests exist.
    """
    if exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
