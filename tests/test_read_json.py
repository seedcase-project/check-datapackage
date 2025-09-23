from json import JSONDecodeError
from pathlib import Path

from pytest import raises

from check_datapackage import read_json


def test_reads(tmp_path: Path) -> None:
    """Correctly reads a JSON file into a dictionary."""
    json_path = tmp_path / "datapackage.json"
    json_path.write_text('{"name": "example", "resources": []}')
    descriptor = read_json(json_path)
    assert descriptor == {"name": "example", "resources": []}


def test_not_a_dict(tmp_path: Path) -> None:
    """Output TypeError if the JSON file does not contain a dictionary."""
    json_path = tmp_path / "datapackage.json"
    json_path.write_text('["not", "a", "dict"]')

    with raises(TypeError):
        read_json(json_path)


def test_not_json(tmp_path: Path) -> None:
    """Output JSONDecodeError if can't be parsed to JSON."""
    json_path = tmp_path / "datapackage.json"
    json_path.write_text('"not", "a", "dict"')

    with raises(JSONDecodeError):
        read_json(json_path)


def test_read_nonexistent_file(tmp_path: Path) -> None:
    """Output FileNotFoundError if the file does not exist."""
    json_path = tmp_path / "nonexistent.json"

    with raises(FileNotFoundError):
        read_json(json_path)
