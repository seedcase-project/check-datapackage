from typing import Any

from pytest import mark, raises

from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.custom_check import CustomCheck
from check_datapackage.examples import (
    example_package_properties,
    example_resource_properties,
)
from check_datapackage.issue import Issue

lowercase_check = CustomCheck(
    jsonpath="$.name",
    message="Name must be lowercase.",
    check=lambda name: name.islower(),
    type="lowercase",
)
resource_name_check = CustomCheck(
    jsonpath="$.resources[*].name",
    message="Resource name must start with 'woolly'.",
    check=lambda name: name.startswith("woolly"),
    type="resource-name",
)


def must_not_be_null(value: Any) -> bool:
    return value is not None


def test_direct_jsonpath():
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    config = Config(custom_checks=[lowercase_check])
    issues = check(properties, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_check.jsonpath,
            type=lowercase_check.type,
            message=lowercase_check.message,
        )
    ]


def test_indirect_jsonpath():
    properties = example_package_properties()
    properties["resources"].append(example_resource_properties())
    properties["resources"][1]["name"] = "not starting with woolly"

    config = Config(custom_checks=[resource_name_check])
    issues = check(properties, config=config)

    assert issues == [
        Issue(
            jsonpath="$.resources[1].name",
            type=resource_name_check.type,
            message=resource_name_check.message,
        ),
    ]


def test_multiple_custom_checks():
    descriptor = example_package_properties()
    descriptor["name"] = "ALLCAPS"
    descriptor["resources"][0]["name"] = "not starting with woolly"
    del descriptor["version"]

    version_check = CustomCheck(
        jsonpath="$.version",
        message="Version is required.",
        type="required",
        check=must_not_be_null,
        check_missing=True,
    )

    config = Config(
        custom_checks=[
            lowercase_check,
            resource_name_check,
            version_check,
        ]
    )
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_check.jsonpath,
            type=lowercase_check.type,
            message=lowercase_check.message,
        ),
        Issue(
            jsonpath="$.resources[0].name",
            type=resource_name_check.type,
            message=resource_name_check.message,
        ),
        Issue(
            jsonpath=version_check.jsonpath,
            type="required",
            message=version_check.message,
        ),
    ]


def test_custom_checks_and_default_checks():
    properties = example_package_properties()
    properties["name"] = "ALLCAPS"
    del properties["resources"]
    config = Config(custom_checks=[lowercase_check])
    issues = check(properties, config=config)

    assert [issue.type for issue in issues] == ["lowercase", "required"]


def test_no_matching_jsonpath():
    properties = example_package_properties()
    custom_check = CustomCheck(
        jsonpath="$.missing",
        message="This check always fails.",
        check=lambda value: False,
        type="always-fail",
    )
    config = Config(custom_checks=[custom_check])
    issues = check(properties, config=config)

    assert issues == []


def test_no_matching_jsonpath_with_check_missing():
    properties = example_package_properties()
    custom_check = CustomCheck(
        jsonpath="$.missing",
        message="This check always fails.",
        check=lambda value: False,
        type="always-fail",
        check_missing=True,
    )
    config = Config(custom_checks=[custom_check])
    issues = check(properties, config=config)

    assert len(issues) == 1


def test_required_check_wildcard():
    descriptor = example_package_properties()
    id_check = CustomCheck(
        jsonpath="$.*.id",
        message="All fields must have an id.",
        type="required",
        check=must_not_be_null,
        check_missing=True,
    )
    config = Config(custom_checks=[id_check])

    issues = check(descriptor, config=config)

    assert len(issues) == 8


def test_required_check_array_wildcard():
    descriptor = example_package_properties()
    descriptor["contributors"] = [
        {"path": "a/path"},
        {"path": "a/path"},
        {"path": "a/path", "name": "a name"},
    ]
    name_check = CustomCheck(
        jsonpath="$.contributors[*].name",
        message="Contributor name is required.",
        type="required",
        check=must_not_be_null,
        check_missing=True,
    )
    config = Config(custom_checks=[name_check])
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath="$.contributors[0].name",
            type=name_check.type,
            message=name_check.message,
        ),
        Issue(
            jsonpath="$.contributors[1].name",
            type=name_check.type,
            message=name_check.message,
        ),
    ]


@mark.parametrize(
    "jsonpath",
    [
        "$",
        "..*",
        "created",
        "$..path",
        "..resources",
        "$.resources[0].*",
        "$.resources[*]",
    ],
)
def test_required_check_cannot_apply_to_ambiguous_path(jsonpath):
    with raises(ValueError):
        CustomCheck(
            jsonpath=jsonpath,
            message="This should fail.",
            type="required",
            check=must_not_be_null,
            check_missing=True,
        )
