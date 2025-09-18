from pytest import mark

from check_datapackage.check import check
from check_datapackage.config import Config

# Without recommendations


def test_passes_matching_descriptor_with_resources():
    """Should pass descriptor matching the schema."""
    descriptor = {
        "name": "a name with spaces",
        "title": "A Title",
        "created": "2024-05-14T05:00:01+00:00",
        "version": "a version",
        "contributors": [{"email": "jane@doe.com"}],
        "sources": [{"email": "jane@doe.com"}],
        "resources": [{"name": "a name", "path": "data.csv"}],
    }

    assert check(descriptor) == []


def test_fails_descriptor_without_resources():
    """Should fail descriptor without resources."""
    descriptor = {"name": "a name with spaces"}

    errors = check(descriptor)

    assert len(errors) == 1
    assert errors[0].validator == "required"
    assert errors[0].json_path == "$.resources"


@mark.parametrize(
    "resources, json_path, num_errors",
    [
        ([], "$.resources", 1),
        ([{}], "$.resources[0].data", 3),
        ([{"name": "a name", "path": "/a/bad/path"}], "$.resources[0].path", 2),
    ],
)
def test_fails_descriptor_with_bad_resources(resources, json_path, num_errors):
    """Should fail descriptor with malformed resources."""
    descriptor = {
        "name": "a name with spaces",
        "resources": resources,
    }

    errors = check(descriptor)

    assert len(errors) == num_errors
    assert errors[0].json_path == json_path


def test_fails_descriptor_with_missing_required_fields():
    """Should fail descriptor with missing required fields."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "licenses": [{"title": "my license"}],
    }

    errors = check(descriptor)

    assert len(errors) == 2
    assert all(error.validator == "required" for error in errors)
    assert {error.json_path for error in errors} == {
        "$.licenses[0].name",
        "$.licenses[0].path",
    }


def test_fails_descriptor_with_bad_type():
    """Should fail descriptor with a field of the wrong type."""
    descriptor = {
        "name": 123,
        "resources": [{"name": "a name", "path": "data.csv"}],
    }
    errors = check(descriptor)

    assert len(errors) == 1
    assert errors[0].validator == "type"
    assert errors[0].json_path == "$.name"


def test_fails_descriptor_with_bad_format():
    """Should fail descriptor with a field of the wrong format."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "homepage": "not a URL",
    }

    errors = check(descriptor)

    assert len(errors) == 1
    assert errors[0].validator == "format"
    assert errors[0].json_path == "$.homepage"


def test_fails_descriptor_with_pattern_mismatch():
    """Should fail descriptor with a field that does not match the pattern."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    errors = check(descriptor)

    assert len(errors) == 1
    assert errors[0].validator == "pattern"
    assert errors[0].json_path == "$.contributors[0].path"


# With recommendations


def test_passes_matching_descriptor_with_recommendations():
    """Should pass descriptor matching recommendations."""
    descriptor = {
        "name": "a-name-with-no-spaces",
        "title": "A Title",
        "id": "123",
        "created": "2024-05-14T05:00:01+00:00",
        "version": "3.2.1",
        "contributors": [{"title": "a contributor"}],
        "sources": [{"title": "a source"}],
        "licenses": [{"name": "a-license"}],
        "resources": [{"name": "a-name-with-no-spaces", "path": "data.csv"}],
    }

    assert check(descriptor, config=Config(strict=True)) == []


def test_fails_descriptor_with_missing_required_fields_with_recommendations():
    """Should fail descriptor with missing required fields."""
    descriptor = {
        "resources": [{"name": "a-name-with-no-spaces", "path": "data.csv"}],
    }

    errors = check(descriptor, config=Config(strict=True))

    assert len(errors) == 3
    assert all(error.validator == "required" for error in errors)


def test_fails_descriptor_violating_recommendations():
    """Should fail descriptor that do not meet the recommendations."""
    descriptor = {
        "name": "a name with spaces",
        "id": "123",
        "version": "not semver",
        "contributors": [{"email": "jane@doe.com"}],
        "sources": [{"email": "jane@doe.com"}],
        "licenses": [{"name": "a-license"}],
        "resources": [{"name": "a name with spaces", "path": "data.csv"}],
    }

    errors = check(descriptor, config=Config(strict=True))

    assert len(errors) == 5
    assert {error.json_path for error in errors} == {
        "$.name",
        "$.version",
        "$.contributors[0].title",
        "$.sources[0].title",
        "$.resources[0].name",
    }
