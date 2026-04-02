"""Functions for the exposed CLI."""

from pathlib import Path
from typing import Any

from seedcase_soil import (
    pretty_print,
    run_without_tracebacks,
    setup_cli,
)

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.read_json import read_json

app = setup_cli(
    name="check-datapackage",
    help=(
        "check-datapackage checks if metadata is compliant with the Data Package"
        "standard"
    ),
    config_name=".cdp.toml",
)


@app.command(name="check")
def check_cmd(
    source: str = "datapackage.json",
    *,
    strict: bool = False,
) -> None:
    """Check a Data Package's metadata against the Data Package standard.

    Outputs a human-readable explanation of any issues found.

    Args:
        source: The local location of a `datapackage.json` file.
        strict: If True, check "SHOULD" properties in addition to "MUST"
            properties from the Data Package standard.
    """
    properties: dict[str, Any] = read_json(Path(source))
    config = Config(strict=strict)
    check(properties, config=config, error=True)
    pretty_print("[green]All checks passed! Your Data Package is valid.[/green]")


def main() -> None:
    """Create an entry point to run the cli without tracebacks."""
    run_without_tracebacks(app)
