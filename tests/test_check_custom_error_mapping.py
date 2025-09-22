from check_datapackage.check import check
from check_datapackage.examples import example_package_descriptor

# Issues at $.resources[x]


def test_pass_with_resource_data_missing():
    descriptor = example_package_descriptor()

    assert check(descriptor) == []


def test_pass_with_resource_path_missing():
    descriptor = example_package_descriptor()
    descriptor["resources"][0]["data"] = [1, 2, 3]
    del descriptor["resources"][0]["path"]

    assert check(descriptor) == []


def test_fail_with_resource_path_and_data_missing():
    descriptor = example_package_descriptor()
    del descriptor["resources"][0]["path"]

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].location == "$.resources[0]"
    assert issues[0].type == "required"


def test_fail_with_both_resource_path_and_data_present():
    descriptor = example_package_descriptor()
    descriptor["resources"][0]["data"] = [1, 2, 3]

    issues = check(descriptor)

    assert len(issues) == 1
    assert issues[0].type == "oneOf"
