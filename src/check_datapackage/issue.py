from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True, frozen=True)
class Issue:
    """An issue found while checking a Data Package descriptor.

    One `Issue` object represents one failed check on one field within the descriptor.

    Attributes:
        jsonpath (string): A [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            format pointing to the field in the input object where the issue is located.
            For example, `$.resources[2].name`.
        type (string): The type of the check that failed (e.g., a JSON schema type such
            as "required", "type", "pattern", or "format", or a custom type). Used to
            exclude specific types of issues.
        message (string): A description of what exactly the issue is.
        instance (Any): The part of the object that failed the check. This field is not
            considered when comparing or hashing `Issue` objects.

    Examples:
        ```{python}
        import check_datapackage as cdp

        issue = cdp.Issue(
            jsonpath="$.resources[2].title",
            type="required",
            message="The `title` field is required but missing at the given JSON path.",
        )
        ```
    """

    jsonpath: str
    type: str
    message: str
    instance: Any = field(default=None, compare=False, hash=False)
