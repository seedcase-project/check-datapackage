from check_datapackage.check import check
from check_datapackage.config import Config
from check_datapackage.custom_check import CustomCheck
from check_datapackage.examples import (
    example_package_descriptor,
    example_resource_descriptor,
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


def test_direct_jsonpath():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    config = Config(custom_checks=[lowercase_check])
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath=lowercase_check.jsonpath,
            type=lowercase_check.type,
            message=lowercase_check.message,
        )
    ]


def test_indirect_jsonpath():
    descriptor = example_package_descriptor()
    descriptor["resources"].append(example_resource_descriptor())
    descriptor["resources"][1]["name"] = "not starting with woolly"

    config = Config(custom_checks=[resource_name_check])
    issues = check(descriptor, config=config)

    assert issues == [
        Issue(
            jsonpath="$.resources[1].name",
            type=resource_name_check.type,
            message=resource_name_check.message,
        ),
    ]


def test_multiple_custom_checks():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    descriptor["resources"][0]["name"] = "not starting with woolly"

    config = Config(custom_checks=[lowercase_check, resource_name_check])
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
    ]


def test_custom_checks_and_default_checks():
    descriptor = example_package_descriptor()
    descriptor["name"] = "ALLCAPS"
    del descriptor["resources"]
    config = Config(custom_checks=[lowercase_check])
    issues = check(descriptor, config=config)

    assert [issue.type for issue in issues] == ["lowercase", "required"]


def test_no_matching_jsonpath():
    descriptor = example_package_descriptor()
    custom_check = CustomCheck(
        jsonpath="$.missing",
        message="This check always fails.",
        check=lambda value: False,
        type="always-fail",
    )
    config = Config(custom_checks=[custom_check])
    issues = check(descriptor, config=config)

    assert issues == []
