from typing import Any

from check_datapackage.check_error import CheckError
from check_datapackage.config import Config
from check_datapackage.constants import DATA_PACKAGE_SCHEMA_PATH
from check_datapackage.internals import (
    _add_package_recommendations,
    _add_resource_recommendations,
    _check_object_against_json_schema,
    _read_json,
)


def check(
    descriptor: dict[str, Any], config: Config = Config(), error: bool = False
) -> list[CheckError]:
    """Checks a Data Package descriptor against the Data Package standard.

    Args:
        descriptor: A Data Package descriptor as a Python dictionary.
        config: Configuration for the checks to be done. See the `Config`
            class for more details, especially about the default values.
        error: Whether to treat any issues found as errors. Defaults
            to `False`, meaning that issues will be returned as a list of `Issue`
            objects. Will internally run `explain()` on the Issues
            if set to `True`.

    Returns:
        A list of `Issue` objects representing any issues found
            while checking the descriptor. If no issues are found, an empty list
            is returned.
    """
    schema = _read_json(DATA_PACKAGE_SCHEMA_PATH)

    if config.strict:
        _add_package_recommendations(schema)
        _add_resource_recommendations(schema)

    return _check_object_against_json_schema(descriptor, schema)
