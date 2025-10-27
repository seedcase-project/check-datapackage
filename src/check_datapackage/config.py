from dataclasses import dataclass, field
from typing import Literal

from check_datapackage.exclusion import Exclusion
from check_datapackage.extensions import CustomCheck


@dataclass
class Config:
    """Configuration for checking a Data Package descriptor.

    Attributes:
        exclusions (list[Exclusion]): Any issues matching any of Exclusion objects will
            be excluded (i.e., removed from the output of the check function).
        custom_checks (list[CustomCheck]): Custom checks listed here will be done in
            addition to checks defined in the Data Package standard.
        strict (bool): Whether to run recommended as well as required checks. If
            True, recommended checks will also be run. Defaults to False.
        version (str): The version of the Data Package standard to check against.
            Defaults to "v2".

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclusion_required = cdp.Exclusion(type="required")
        license_check = cdp.CustomCheck(
            type="only-mit",
            jsonpath="$.licenses[*].name",
            message="Data Packages may only be licensed under MIT.",
            check=lambda license_name: license_name == "mit",
        )
        config = cdp.Config(
            exclusions=[exclusion_required],
            custom_checks=[license_check],
        )
        ```
    """

    exclusions: list[Exclusion] = field(default_factory=list)
    custom_checks: list[CustomCheck] = field(default_factory=list)
    strict: bool = False
    version: Literal["v1", "v2"] = "v2"
