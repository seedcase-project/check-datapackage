"""Functions for the exposed CLI."""

from typing import Any

from cyclopts import App, Parameter
from cyclopts.help import ColumnSpec, DefaultFormatter, DescriptionRenderer
from rich import print as rprint
from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.panel import Panel
from rich.text import Text
from seedcase_flower.parse_source import Address, parse_source

from check_datapackage.check import check, explain
from check_datapackage.config import Config
from check_datapackage.internals import _format_param_help
from check_datapackage.read_properties import read_properties

app = App(
    name="check-datapackage",
    help="Check your Data Package's metadata against the Data Package standard.",
    help_formatter=DefaultFormatter(
        column_specs=(
            ColumnSpec(renderer=_format_param_help),
            ColumnSpec(renderer=DescriptionRenderer(newline_metadata=True)),
        )
    ),
    default_parameter=Parameter(negative=(), show_default=True),
)
app.register_install_completion_command()


@app.command(name="check")
def check_cmd(
    source: str = "datapackage.json",
    *,
    strict: bool = False,
) -> None:
    """Check a Data Package's metadata against the Data Package standard.

    Reads a Data Package file and validates its properties against the
    Data Package standard. Outputs a human-readable explanation of any
    issues found and exits with a non-zero exit code if issues are found.

    Args:
        source: The location of a `datapackage.json` file. Defaults to a
            file or folder path. Can also be an `https:` source to a
            remote `datapackage.json` or a `github:` / `gh:` pointing to a
            repo with a `datapackage.json` in the repo root (in the format
            `gh:org/repo`, which can also include reference to a tag or
            branch, such as `gh:org/repo@main` or `gh:org/repo@1.0.1`).
        strict: If True, check "SHOULD" properties in addition to "MUST"
            properties from the Data Package standard. Defaults to False.
    """
    address: Address = parse_source(source)
    properties: dict[str, Any] = read_properties(address.value, local=address.local)
    config = Config(strict=strict)
    issues = check(properties, config=config, error=False)

    if issues:
        rprint(explain(issues))
        raise SystemExit(1)

    rprint("[green]All checks passed! Your Data Package is valid.[/green]")


def _pretty_print_error(e: Exception) -> None:
    console = Console(stderr=True)
    text = Text.from_markup(str(e))
    pretty_text = ReprHighlighter()(text)
    console.print(
        Panel(
            pretty_text,
            title=type(e).__name__,
            border_style="red",
            title_align="left",
        )
    )


def main() -> None:
    """Suppress traceback when running from CLI."""
    try:
        app()
    except Exception as e:
        _pretty_print_error(e)
        raise SystemExit(1)
