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
    """Checks that `descriptor` matches the Data Package standard.

    All mismatches are collected before issues are flagged.

    The schema loaded or constructed in this function overrides any values specified
    in the `$schema` attribute of `descriptor`, including the default value.

    Args:
        descriptor: The Data Package descriptor to check.
        config: Configuration to customise which issues to flag.
        error: A boolean that controls whether the function errors out or returns a
            value if any issues are found.

    Returns:
        A list of issues. An empty list if no issues are found.
    """
    schema = _read_json(DATA_PACKAGE_SCHEMA_PATH)

    if config.strict:
        _add_package_recommendations(schema)
        _add_resource_recommendations(schema)

    return _check_object_against_json_schema(descriptor, schema)
