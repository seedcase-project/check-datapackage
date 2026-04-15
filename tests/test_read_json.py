from pathlib import Path

from pytest import raises
from seedcase_soil.errors import FileDoesNotExistError, JSONFormatError

from check_datapackage import parse_source, read_properties


def test_reads(tmp_path: Path) -> None:
    """Correctly reads a JSON file into a dictionary."""
    json_path = tmp_path / "datapackage.json"
    json_path.write_text('{"name": "example", "resources": []}')
    properties = read_properties(parse_source(str(json_path)))
    assert properties == {"name": "example", "resources": []}


def test_not_json(tmp_path: Path) -> None:
    """Output JSONFormatError if file can't be parsed as JSON."""
    json_path = tmp_path / "datapackage.json"
    json_path.write_text('"not", "a", "dict"')

    with raises(JSONFormatError):
        read_properties(parse_source(str(json_path)))


def test_read_nonexistent_file(tmp_path: Path) -> None:
    """Output FileDoesNotExistError if the file does not exist."""
    json_path = tmp_path / "nonexistent.json"

    with raises(FileDoesNotExistError):
        read_properties(parse_source(str(json_path)))
