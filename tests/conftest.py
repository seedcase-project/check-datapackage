import json
import os

import pytest


@pytest.fixture
def datapackage():
    """Returns a data package dict with resources."""
    return {
        "name": "test-package",
        "title": "Test Package",
        "description": "A test datapackage",
        "version": "1.0.0",
        "licenses": [{"name": "MIT"}],
        "resources": [
            {
                "name": "data",
                "path": "data.csv",
                "schema": {
                    "fields": [
                        {"name": "id", "type": "integer"},
                        {"name": "name", "type": "string"},
                    ]
                },
            },
        ],
    }


@pytest.fixture
def datapackage_path(tmp_path, datapackage):
    """Create a temporary datapackage.json file and return its path as a string."""
    file_path = tmp_path / "datapackage.json"
    file_path.write_text(json.dumps(datapackage))
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
