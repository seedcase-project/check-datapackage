import os

import pytest
from seedcase_soil import (
    Example,
    read_properties,
    write_properties,
)


@pytest.fixture
def datapackage():
    """Return a datapackage dict with resources."""
    return read_properties(Example.simple.address)


@pytest.fixture
def datapackage_path(tmp_path, datapackage):
    """Create a temporary datapackage.json file and return its path as a string."""
    file_path = tmp_path / "datapackage.json"
    write_properties(datapackage, file_path)
    return str(file_path)


# Can get debug output by using `CDP_DEBUG=true uv run pytest -sv`
def pytest_report_teststatus(report):
    if os.getenv("CDP_DEBUG"):
        if report.when == "call":
            # Add newlines to separate test results
            category = report.outcome
            shortletter = "\n\n"  # dot / F / X / etc.
            verbose = "\n\n"  # ("PASSED", "FAILED", ...)

            return category, shortletter, verbose

    return None
