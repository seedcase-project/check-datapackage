import os


# Can get debug output by using `CDP_DEBUG=true uv run pytest -sv`
def pytest_report_teststatus(report, config):
    if os.getenv("CDP_DEBUG"):
        if report.when == "call":
            # Add newlines to separate test results
            category = report.outcome
            shortletter = "\n\n"  # dot / F / X / etc.
            verbose = "\n\n"  # ("PASSED", "FAILED", ...)

            return category, shortletter, verbose

    return None
