"""Tests for the CLI commands."""

import json

import pytest

from check_datapackage.check import DataPackageError
from check_datapackage.cli import app


@pytest.fixture
def mock_read_json(mocker):
    """Mock read_json to isolate CLI tests from filesystem resolution."""
    return mocker.patch("check_datapackage.cli.read_json")


@pytest.fixture
def mock_check(mocker):
    """Mock check to isolate CLI from validation logic."""
    return mocker.patch("check_datapackage.cli.check")


# Testing CLI invocation ====


def test_check_with_mocked_internals(mock_read_json, mock_check):
    """Isolate CLI behaviour by mocking internal helpers."""
    mock_read_json.return_value = {"name": "test-package"}
    mock_check.return_value = []

    app(["check", "datapackage.json"], result_action="return_value")

    mock_read_json.assert_called_once()
    mock_check.assert_called_once()


# File-based config ====


def test_check_reads_source_from_cdp_toml(tmp_path, monkeypatch):
    """Check args specified in .cdp.toml should overwrite the default values."""
    toml_path = tmp_path / ".cdp.toml"
    toml_path.write_text('source = "custom.json"\nstrict = true\n')

    monkeypatch.chdir(tmp_path)

    _, bound, _ = app.parse_args(["check"])
    assert bound.arguments["source"] == "custom.json"
    assert bound.arguments["strict"] is True


# Success and error handling ====


def test_check_valid_datapackage_succeeds(
    capsys, datapackage_path, tmp_path, monkeypatch
):
    """A valid datapackage should pass checks."""
    monkeypatch.chdir(tmp_path)
    app(["check", datapackage_path], result_action="return_value")

    out = capsys.readouterr().out
    assert "All checks passed!" in out


def test_check_missing_datapackage_raises_error(tmp_path, monkeypatch):
    """Missing datapackage file should raise an error."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        app(["check", "nonexistent.json"], result_action="return_value")


def test_check_raises_error_on_validation_failure(tmp_path, monkeypatch):
    """Check should raise DataPackageError when validation fails."""

    invalid_datapackage = {"name": "invalid-name!"}
    file_path = tmp_path / "datapackage.json"
    file_path.write_text(json.dumps(invalid_datapackage))

    monkeypatch.chdir(tmp_path)

    with pytest.raises(DataPackageError):
        app(["check", str(file_path)], result_action="return_value")
