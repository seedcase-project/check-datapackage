"""Tests for the CLI commands."""

import json

import pytest
from seedcase_soil.errors import FileDoesNotExistError

from check_datapackage.check import DataPackageError
from check_datapackage.cli import app
from check_datapackage.exclusion import Exclusion
from check_datapackage.extensions import Extensions, RequiredCheck


@pytest.fixture
def mock_parse_source(mocker):
    """Mock parse_source to isolate CLI tests from source resolution."""
    return mocker.patch("check_datapackage.cli.parse_source")


@pytest.fixture
def mock_read_properties(mocker):
    """Mock read_properties to isolate CLI tests from file I/O."""
    return mocker.patch("check_datapackage.cli.read_properties")


@pytest.fixture
def mock_check(mocker):
    """Mock check to isolate CLI from logic."""
    return mocker.patch("check_datapackage.cli.check")


# Testing CLI invocation ====


def test_check_with_mocked_internals(
    tmp_path,
    monkeypatch,
    mock_parse_source,
    mock_read_properties,
    mock_check,
):
    """Isolate CLI behaviour by mocking internal helpers."""
    fake_source = object()
    mock_parse_source.return_value = fake_source
    mock_read_properties.return_value = {"name": "test-package"}
    mock_check.return_value = []

    monkeypatch.chdir(tmp_path)
    app(["check", "datapackage.json"], result_action="return_value")

    mock_parse_source.assert_called_once_with("datapackage.json")
    mock_read_properties.assert_called_once_with(fake_source)
    mock_check.assert_called_once()
    args, kwargs = mock_check.call_args
    assert args[0] == mock_read_properties.return_value
    assert kwargs["error"] is True
    assert kwargs["config"].strict is False


# File-based config ====


def test_check_reads_source_from_cdp_toml(tmp_path, monkeypatch):
    """Check args specified in .cdp.toml should overwrite the default values."""
    toml_path = tmp_path / ".cdp.toml"
    toml_path.write_text("strict = true\n")

    monkeypatch.chdir(tmp_path)

    _, bound, _ = app.parse_args(["check"])
    assert bound.arguments["strict"] is True


def test_check_reads_exclusions_from_cdp_toml(tmp_path, monkeypatch):
    """Top-level exclusions in .cdp.toml should bind to check command args."""
    toml_path = tmp_path / ".cdp.toml"
    toml_path.write_text(
        "\n".join(
            [
                "[[exclusions]]",
                'jsonpath = "$.resources"',
                "",
                "[[exclusions]]",
                'jsonpath = "$.contributors[*].path"',
                'type = "format"',
            ]
        )
    )

    monkeypatch.chdir(tmp_path)

    _, bound, _ = app.parse_args(["check"])
    exclusions = bound.arguments["exclusions"]

    assert exclusions == [
        Exclusion(jsonpath="$.resources"),
        Exclusion(jsonpath="$.contributors[*].path", type="format"),
    ]


def test_check_passes_exclusions_from_config_to_check(
    tmp_path,
    monkeypatch,
    mock_parse_source,
    mock_read_properties,
    mock_check,
):
    """Exclusions loaded from config should be included in Config passed to check."""
    toml_path = tmp_path / ".cdp.toml"
    toml_path.write_text(
        "\n".join(
            [
                "[[exclusions]]",
                'jsonpath = "$.resources"',
                "",
                "[[exclusions]]",
                'jsonpath = "$.contributors[*].path"',
                'type = "format"',
            ]
        )
    )

    fake_source = object()
    mock_parse_source.return_value = fake_source
    mock_read_properties.return_value = {"name": "test-package"}
    mock_check.return_value = []

    monkeypatch.chdir(tmp_path)
    app(["check", "datapackage.json"], result_action="return_value")

    _, kwargs = mock_check.call_args
    assert kwargs["config"].exclusions == [
        Exclusion(jsonpath="$.resources"),
        Exclusion(jsonpath="$.contributors[*].path", type="format"),
    ]


def test_check_reads_extensions_from_cdp_toml(tmp_path, monkeypatch):
    """Top-level extensions in .cdp.toml should bind to check command args."""
    toml_path = tmp_path / ".cdp.toml"
    toml_path.write_text(
        "\n".join(
            [
                "[[extensions.required_checks]]",
                'jsonpath = "$.description"',
                'message = "Description is required."',
                "",
                "[[extensions.required_checks]]",
                'jsonpath = "$.contributors[*].email"',
                'message = "All contributors need an email address."',
            ]
        )
    )

    monkeypatch.chdir(tmp_path)

    _, bound, _ = app.parse_args(["check"])
    extensions = bound.arguments["extensions"]

    assert extensions == Extensions(
        required_checks=[
            RequiredCheck(
                jsonpath="$.description",
                message="Description is required.",
            ),
            RequiredCheck(
                jsonpath="$.contributors[*].email",
                message="All contributors need an email address.",
            ),
        ]
    )


def test_check_passes_extensions_from_config_to_check(
    tmp_path,
    monkeypatch,
    mock_parse_source,
    mock_read_properties,
    mock_check,
):
    """Extensions loaded from config should be included in Config passed to check."""
    toml_path = tmp_path / ".cdp.toml"
    toml_path.write_text(
        "\n".join(
            [
                "[[extensions.required_checks]]",
                'jsonpath = "$.description"',
                'message = "Description is required."',
            ]
        )
    )

    fake_source = object()
    mock_parse_source.return_value = fake_source
    mock_read_properties.return_value = {"name": "test-package"}
    mock_check.return_value = []

    monkeypatch.chdir(tmp_path)
    app(["check", "datapackage.json"], result_action="return_value")

    _, kwargs = mock_check.call_args
    assert kwargs["config"].extensions == Extensions(
        required_checks=[
            RequiredCheck(
                jsonpath="$.description",
                message="Description is required.",
            )
        ]
    )


# Success and error handling ====


def test_check_valid_datapackage_succeeds(
    capsys, datapackage_path, tmp_path, monkeypatch
):
    """A correct data package should pass checks."""
    monkeypatch.chdir(tmp_path)
    app(["check", datapackage_path], result_action="return_value")

    out = capsys.readouterr().out
    assert "All checks passed!" in out


def test_check_missing_datapackage_raises_error(tmp_path, monkeypatch):
    """Missing datapackage file should raise an error."""
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileDoesNotExistError):
        app(["check", "nonexistent.json"], result_action="return_value")


def test_check_raises_error_on_failure(tmp_path, monkeypatch):
    """Failed check should give DataPackageError."""

    wrong_datapackage = {"name": "bad-name!"}
    file_path = tmp_path / "datapackage.json"
    file_path.write_text(json.dumps(wrong_datapackage))

    monkeypatch.chdir(tmp_path)

    with pytest.raises(DataPackageError):
        app(["check", str(file_path)], result_action="return_value")
