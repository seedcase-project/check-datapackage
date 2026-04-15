from importlib.resources import files

from seedcase_soil import Address

GROUP_ERRORS = {"allOf", "anyOf", "oneOf"}

DATA_PACKAGE_SCHEMA_ADDRESS = Address(
    value=str(files("check_datapackage.schemas").joinpath("data-package-2-0.json")),
    local=True,
)

FIELD_TYPES = [
    "string",
    "number",
    "integer",
    "date",
    "time",
    "datetime",
    "year",
    "yearmonth",
    "boolean",
    "object",
    "geopoint",
    "geojson",
    "array",
    "duration",
    "any",
]
