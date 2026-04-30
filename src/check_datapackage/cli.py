"""Functions for the exposed CLI."""

from typing import Annotated, Any

from cyclopts import Parameter
from seedcase_soil import (
    Address,
    parse_source,
    pretty_print,
    read_properties,
    run_without_tracebacks,
    setup_cli,
)

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.exclusion import Exclusion
from check_datapackage.extensions import Extensions

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
    /,  # End of positional-only args
    *,  # Start of keyword-only params
    strict: bool = False,
    exclusions: Annotated[list[Exclusion], Parameter(show=False)] = [],
    extensions: Annotated[Extensions, Parameter(show=False)] = Extensions(),
) -> None:
    """Check a Data Package's metadata against the Data Package standard.

    Outputs a human-readable explanation of any issues found.

    Args:
        source: The location of a `datapackage.json`, defaults to a file or folder
            path. Can also be an `https:` source to a remote `datapackage.json` or a
            `github:` / `gh:` pointing to a repo with a `datapackage.json`
            in the repo root (in the format `gh:org/repo`, which can also include
            reference to a tag or branch, such as `gh:org/repo@main` or
            `gh:org/repo@1.0.1`).
        strict: If True, check "SHOULD" properties in addition to "MUST"
            properties from the Data Package standard.
        exclusions: A hidden CLI/config parameter for excluding issues by JSONPath
            and/or issue type.
        extensions: A hidden CLI/config parameter for adding extra checks.
    """
    address: Address = parse_source(source)
    properties: dict[str, Any] = read_properties(address)
    config = Config(strict=strict, exclusions=exclusions, extensions=extensions)
    check(properties, config=config, error=True)
    pretty_print("[green]All checks passed![/green]")


def main() -> None:
    """Create an entry point to run the cli without tracebacks."""
    run_without_tracebacks(app)
