from typing import Literal

from pydantic import BaseModel

from check_datapackage.exclusion import Exclusion
from check_datapackage.extensions import Extensions


class Config(BaseModel, frozen=True):
    """Configuration for checking a Data Package descriptor.

    Attributes:
        exclusions (list[Exclusion]): Any issues matching any of Exclusion objects will
            be excluded (i.e., removed from the output of the check function).
        extensions (Extensions): Additional checks (called extensions)
            that supplement those specified by the Data Package standard.
        strict (bool): Whether to include "SHOULD" checks in addition to "MUST" checks
            from the Data Package standard. If True, "SHOULD" checks will also be
            included. Defaults to False.
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
        required_title_check = cdp.RequiredCheck(
            jsonpath="$.title",
            message="A title is required.",
        )
        config = cdp.Config(
            exclusions=[exclusion_required],
            extensions=cdp.Extensions(
                custom_checks=[license_check],
                required_checks=[required_title_check]
            )
        )

        # check(properties, config=config)
        ```
    """

    exclusions: list[Exclusion] = []
    extensions: Extensions = Extensions()
    strict: bool = False
    version: Literal["v1", "v2"] = "v2"
