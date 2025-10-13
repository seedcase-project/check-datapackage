import re
from dataclasses import dataclass
from typing import Any, Callable

from check_datapackage.internals import (
    DescriptorField,
    _filter,
    _flat_map,
    _get_fields_at_jsonpath,
    _map,
)
from check_datapackage.issue import Issue


@dataclass(frozen=True)
class Rule:
    """A custom check to be done on a Data Package descriptor.

    Attributes:
        jsonpath (str): The location of the field or fields, expressed in [JSON
            path](https://jg-rp.github.io/python-jsonpath/syntax/) notation, to which
            the rule applies (e.g., `$.resources[*].name`).
        message (str): The message that is shown when the rule is violated.
        check (Callable[[Any], bool]): A function that expresses how compliance with the
            rule is checked. It takes the value at the `jsonpath` location as input and
            returns true if the rule is met, false if it isn't.
        type (str): An identifier for the rule. It will be shown in error messages and
            can be used to exclude the rule. Each rule should have a unique `type`.

    Examples:
        ```{python}
        import check_datapackage as cdp

        license_rule = cdp.Rule(
            type="only-mit",
            jsonpath="$.licenses[*].name",
            message="Data Packages may only be licensed under MIT.",
            check=lambda license_name: license_name == "mit",
        )
        ```
    """

    jsonpath: str
    message: str
    check: Callable[[Any], bool]
    type: str = "custom"

    def apply(self, descriptor: dict[str, Any]) -> list[Issue]:
        """Checks the descriptor against this rule and creates issues on failure.

        Args:
            descriptor: The descriptor to check.

        Returns:
            A list of `Issue`s.
        """
        matching_fields = _get_fields_at_jsonpath(self.jsonpath, descriptor)
        return _get_issues(self, matching_fields)


class RequiredRule(Rule):
    """A rule that checks that a field is present (i.e. not None).

    Attributes:
        jsonpath (str): The location of the field or fields, expressed in [JSON
            path](https://jg-rp.github.io/python-jsonpath/syntax/) notation, to which
            the rule applies (e.g., `$.resources[*].name`).
        message (str): The message that is shown when the rule is violated.

    Examples:
        ```{python}
        import check_datapackage as cdp
        required_title_rule = cdp.RequiredRule(
            jsonpath="$.title",
            message="A title is required.",
        )
        ```
    """

    _field_name: str

    def __init__(self, jsonpath: str, message: str):
        """Initializes the `RequiredRule`."""
        field_name_match = re.search(r"\.(\w+)$", jsonpath)
        if not field_name_match:
            raise ValueError(
                "A `RequiredRule` must point to an object field that is not an array"
                " item, e.g., `$.title` or `$.resources[*].name`."
            )

        self._field_name = field_name_match.group(1)
        super().__init__(
            jsonpath=jsonpath,
            message=message,
            check=lambda value: value is not None,
            type="required",
        )

    def apply(self, descriptor: dict[str, Any]) -> list[Issue]:
        """Checks the descriptor against this rule and creates issues on failure.

        Args:
            descriptor: The descriptor to check.

        Returns:
            A list of `Issue`s.
        """
        matching_fields = _get_fields_at_jsonpath(self.jsonpath, descriptor)
        matching_paths = _map(matching_fields, lambda field: field.jsonpath)
        parent_path = self.jsonpath.rstrip(f".{self._field_name}")
        matching_parents = _get_fields_at_jsonpath(parent_path, descriptor)
        parent_paths = _map(
            matching_parents, lambda parent: f"{parent.jsonpath}.{self._field_name}"
        )
        missing_paths = _filter(parent_paths, lambda path: path not in matching_paths)
        missing_fields = _map(
            missing_paths,
            lambda path: DescriptorField(jsonpath=path, value=None),
        )

        return _get_issues(self, matching_fields + missing_fields)


def _get_issues(rule: Rule, matching_fields: list[DescriptorField]) -> list[Issue]:
    """Checks matching fields against the rule and creates issues on failure."""
    failed_fields = _filter(matching_fields, lambda field: not rule.check(field.value))
    return _map(
        failed_fields,
        lambda field: Issue(
            jsonpath=field.jsonpath, type=rule.type, message=rule.message
        ),
    )


def apply_rules(rules: list[Rule], descriptor: dict[str, Any]) -> list[Issue]:
    """Checks the descriptor for all rules and creates issues for fields that fail.

    Args:
        rules: The rules to apply to the descriptor.
        descriptor: The descriptor to check.

    Returns:
        A list of `Issue`s.
    """
    return _flat_map(
        rules,
        lambda rule: rule.apply(descriptor),
    )
