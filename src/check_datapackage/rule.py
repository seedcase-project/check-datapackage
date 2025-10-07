from dataclasses import dataclass
from typing import Any, Callable

from check_datapackage.internals import _filter_map, _get_fields_at_jsonpath
from check_datapackage.issue import Issue


@dataclass
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


def apply_rule(rule: Rule, descriptor: dict[str, Any]) -> list[Issue]:
    """Checks the descriptor against the rule and creates issues for fields that fail.

    Args:
        rule: The rule to apply to the descriptor.
        descriptor: The descriptor to check.

    Returns:
        A list of `Issue`s.
    """
    matching_fields = _get_fields_at_jsonpath(rule.jsonpath, descriptor)

    return _filter_map(
        items=matching_fields,
        map_fn=lambda field: Issue(
            jsonpath=field.jsonpath, type=rule.type, message=rule.message
        ),
        condition=lambda field: not rule.check(field.value),
    )
