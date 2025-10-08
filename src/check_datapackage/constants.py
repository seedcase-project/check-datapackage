from enum import Enum
from importlib.resources import files
from pathlib import Path


# Data Package standard required fields and their types
class RequiredFieldType(str, Enum):
    """A class enumerating allowed types for required fields."""

    str = "str"
    list = "list"
    any = "any"


GROUP_ERRORS = {"allOf", "anyOf", "oneOf"}

DATA_PACKAGE_SCHEMA_PATH = Path(
    str(files("check_datapackage.schemas").joinpath("data-package-schema.json"))
)

NAME_PATTERN = r"^[a-z0-9._-]+$"

PACKAGE_RECOMMENDED_FIELDS = {
    "name": RequiredFieldType.str,
    "id": RequiredFieldType.str,
    "licenses": RequiredFieldType.list,
}

PACKAGE_REQUIRED_FIELDS = {
    "resources": RequiredFieldType.list,
}

RESOURCE_REQUIRED_FIELDS = {
    "name": RequiredFieldType.str,
    "path": RequiredFieldType.str,
    "data": RequiredFieldType.any,
}

# From https://semver.org/#is-there-a-suggested-regular-expression-regex-to-check-a-semver-string
SEMVER_PATTERN = (
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0"
    r"|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+(?P<buildmetadata>"
    r"[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
