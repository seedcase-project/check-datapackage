from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Rule:
    """A custom check to be done on a Data Package descriptor.

    Attributes:
        target (str): The location of the field or fields, expressed in [JSON
            path](https://jg-rp.github.io/python-jsonpath/syntax/) notation, to which
            the rule applies (e.g., `$.resources[*].name`).
        message (str): The message that is shown when the rule is violated.
        check (Callable[[Any], bool]): A function that expresses how compliance with the
            rule is checked. It takes the value at the `target` location as input and
            returns true if the rule is met, false if it isn't.
        type (str): An identifier for your rule. This is what will show up in
            error messages and what you will use if you want to exclude your
            rule. Each `Rule` should have a unique `type`.

    Examples:
        ```{python}
        import check_datapackage as cdp

        license_rule = cdp.Rule(
            type="only-mit",
            target="$.licenses[*].name",
            message="Data Packages may only be licensed under MIT.",
            check=lambda license_name: license_name == "mit",
        )
        ```
    """

    target: str
    message: str
    check: Callable[[Any], bool]
    type: str = "custom"
