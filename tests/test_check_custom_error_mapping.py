from pytest import mark

from check_datapackage.check import check
from check_datapackage.examples import (
    example_package_descriptor,
    example_resource_descriptor,
)

# Issues at $.resources[x]


def test_pass_with_resource_data_missing():
    descriptor = example_package_descriptor()

    assert check(descriptor) == []


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
    assert issues[0].location == "$.resources[0]"
    assert issues[0].type == "required"
    assert issues[1].location == "$.resources[0].name"
    assert issues[1].type == "required"


def test_fail_with_multiple_resources():
    descriptor = example_package_descriptor()
    descriptor["resources"].append(example_resource_descriptor())
    del descriptor["resources"][0]["path"]
    del descriptor["resources"][1]["path"]

    issues = check(descriptor)

    assert len(issues) == 2
    assert issues[0].location == "$.resources[0]"
    assert issues[0].type == "required"
    assert issues[1].location == "$.resources[1]"
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
    assert issues[0].location == location
