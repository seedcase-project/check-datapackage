from dataclasses import dataclass, field
from typing import Literal

from check_datapackage.exclude import Exclude
from check_datapackage.rule import Rule


@dataclass
class Config:
    """Configuration for checking a Data Package descriptor.

    Attributes:
        exclude (list[Exclude]): Any issues matching any of these exclusions will be
            ignored (i.e., removed from the output of the check function).
        rules (list[Rule]): Custom checks listed here will be done in addition
            to checks defined in the Data Package standard.
        strict (bool): Whether to run recommended as well as required checks. If
            True, recommended checks will also be run. Defaults to False.
        version (str): The version of the Data Package standard to check against.
            Defaults to "v2".

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclude_required = cdp.Exclude(type="required")
        license_rule = cdp.Rule(
            type="only-mit",
            target="$.licenses[*].name",
            message="Data Packages may only be licensed under MIT.",
            check=lambda license_name: license_name == "mit",
        )
        config = cdp.Config(exclude=[exclude_required], rules=[license_rule])
        ```
    """

    exclude: list[Exclude] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    strict: bool = False
    version: Literal["v1", "v2"] = "v2"
