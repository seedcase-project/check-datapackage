from pytest import mark

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.examples import (
    example_package_descriptor,
    example_resource_descriptor,
)
from check_datapackage.exclude import Exclude
from tests.test_custom_check import lowercase_check

# Without recommendations


def test_passes_matching_descriptor_with_resources():
    """Should pass descriptor matching the schema."""
    descriptor = example_package_descriptor()

    assert check(descriptor) == []


def test_fails_descriptor_without_resources():
    """Should fail descriptor without resources."""
    descriptor = {"name": "a name with spaces"}

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "required"
    assert issues[0].jsonpath == "$.resources"


def test_fails_descriptor_with_empty_resources():
    """Should fail descriptor with an empty resources array."""
    descriptor = {
        "name": "a name with spaces",
        "resources": [],
    }

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].jsonpath == "$.resources"


def test_fails_descriptor_with_bad_type():
    """Should fail descriptor with a field of the wrong type."""
    descriptor = {
        "name": 123,
        "resources": [{"name": "a name", "path": "data.csv"}],
    }
    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "type"
    assert issues[0].jsonpath == "$.name"


def test_fails_descriptor_with_bad_format():
    """Should fail descriptor with a field of the wrong format."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "homepage": "not a URL",
    }

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "format"
    assert issues[0].jsonpath == "$.homepage"


def test_fails_descriptor_with_pattern_mismatch():
    """Should fail descriptor with a field that does not match the pattern."""
    descriptor = {
        "name": "a name",
        "resources": [{"name": "a name", "path": "data.csv"}],
        "contributors": [{"path": "/a/bad/path"}],
    }

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "pattern"
    assert issues[0].jsonpath == "$.contributors[0].path"


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

    issues = check(descriptor, config=Config(strict=True))

    assert len(issues) == 3
    assert all(issue.type == "required" for issue in issues)


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

    issues = check(descriptor, config=Config(strict=True))

    assert len(issues) == 5
    assert {issue.jsonpath for issue in issues} == {
        "$.name",
        "$.version",
        "$.contributors[0].title",
        "$.sources[0].title",
        "$.resources[0].name",
    }


def test_exclude_not_excluding_rule():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    del descriptor["resources"]
    exclude_required = Exclude(type="required")
    config = Config(custom_checks=[lowercase_check], exclude=[exclude_required])

    issues = check(descriptor, config=config)

    assert len(issues) == 1
    assert issues[0].type == "lowercase"


def test_exclude_excluding_rule():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    exclude_lowercase = Exclude(type=lowercase_check.type)
    config = Config(custom_checks=[lowercase_check], exclude=[exclude_lowercase])

    issues = check(descriptor, config=config)

    assert issues == []


# Issues at $.resources[x]


def test_pass_with_resource_path_missing():
    descriptor = example_package_descriptor()
    descriptor["resources"][0]["data"] = [1, 2, 3]
    del descriptor["resources"][0]["path"]

    assert check(descriptor) == []


def test_fail_with_resource_name_path_and_data_missing():
    descriptor = example_package_descriptor()
    del descriptor["resources"][0]["name"]
    del descriptor["resources"][0]["path"]

    issues = check(descriptor)

    assert len(issues) == 2
    assert issues[0].jsonpath == "$.resources[0]"
    assert issues[0].type == "required"
    assert issues[1].jsonpath == "$.resources[0].name"
    assert issues[1].type == "required"


def test_fail_with_multiple_resources():
    descriptor = example_package_descriptor()
    descriptor["resources"].append(example_resource_descriptor())
    del descriptor["resources"][0]["path"]
    del descriptor["resources"][1]["path"]

    issues = check(descriptor)

    assert len(issues) == 2
    assert issues[0].jsonpath == "$.resources[0]"
    assert issues[0].type == "required"
    assert issues[1].jsonpath == "$.resources[1]"
    assert issues[1].type == "required"


def test_fail_with_both_resource_path_and_data_present():
    descriptor = example_package_descriptor()
    descriptor["resources"][0]["data"] = [1, 2, 3]

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "oneOf"


def test_fail_one_resource_pass_another():
    descriptor = example_package_descriptor()
    resource2 = example_resource_descriptor()
    descriptor["resources"].append(resource2)
    del descriptor["resources"][0]["path"]

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "required"


# Issues at $.resources[x].path


@mark.parametrize(
    "path, location, type",
    [
        (123, "$.resources[0].path", "type"),
        ("/bad/path", "$.resources[0].path", "pattern"),
        ([], "$.resources[0].path", "minItems"),
        ([123], "$.resources[0].path[0]", "type"),
        (["/bad/path"], "$.resources[0].path[0]", "pattern"),
    ],
)
def test_fail_with_bad_resource_path(path, location, type):
    descriptor = example_package_descriptor()
    descriptor["resources"][0]["path"] = path

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == type
    assert issues[0].jsonpath == location
