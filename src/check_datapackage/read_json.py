from json import JSONDecodeError, loads
from pathlib import Path
from typing import Any


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
        descriptor: Any = loads(path.read_text())
    except JSONDecodeError as err:
        raise JSONDecodeError(
            f"We couldn't parse the path {path} as JSON. Is there a typo or other "
            "issue in the file?",
            doc=err.doc,
            pos=err.pos,
        ) from None  # To hide the original traceback

    if not isinstance(descriptor, dict):  # type: ignore[reportNecessaryIsInstance, unused-ignore]
        raise TypeError(
            f"The file {path} should only have a dictionary (`dict`) object "
            f"but we found it has the type `{type(descriptor)}`. Are there "
            "missing curly brackets `{}` in the file? Maybe at the start or "
            "end of the file?"
        )

    return descriptor
