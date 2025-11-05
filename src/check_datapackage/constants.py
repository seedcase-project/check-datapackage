from importlib.resources import files
from pathlib import Path

GROUP_ERRORS = {"allOf", "anyOf", "oneOf"}

DATA_PACKAGE_SCHEMA_PATH = Path(
    str(files("check_datapackage.schemas").joinpath("data-package-2-0.json"))
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
