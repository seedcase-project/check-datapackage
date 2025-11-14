from json import JSONDecodeError, loads
from pathlib import Path
from typing import Any, cast


def read_json(path: Path) -> dict[str, Any]:
    """Reads `datapackage.json` into a Python dictionary.

    Args:
        path: The path to the `datapackage.json` file to read.

    Returns:
        The contents of the JSON file as a Python dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        JSONDecodeError: If the contents of the file cannot be de-serialised as JSON.
        TypeError: If the contents of the JSON file aren't converted to a Python
            dictionary.
    """
    try:
        properties: Any = loads(path.read_text())
    except JSONDecodeError as error:
        raise JSONDecodeError(
            f"The path {path} couldn't be parsed as JSON. Is there a typo or other "
            "issue in the file?",
            doc=error.doc,
            pos=error.pos,
        ) from None  # To hide the original traceback

    if not isinstance(properties, dict):
        raise TypeError(
            f"The file {path} should parse into a Python dictionary (`dict`) "
            f"but it converts to the type `{type(properties)}`. Is the file "
            "missing a curly bracket `{` at the beginning or `}` at the end?"
        ) from None  # To hide the original traceback

    return cast(dict[str, Any], properties)
