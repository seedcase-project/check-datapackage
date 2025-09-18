from dataclasses import dataclass


@dataclass
class Exclude:
    """Exclude issues when checking a Data Package descriptor.

    When both `target` and `type` are provided, an issue has to match both to be
    excluded.

    Attributes:
        target (str | None): [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            to the field or fields in the input object where issues should be ignored,
            e.g., `$.resources[*].name`. Needs to point to the location in the
            descriptor of the issue to ignore. If not provided, issues of the given
            `type` will be excluded for all fields.
        type (str | None): The type of the issue to ignore (e.g., "required" or
            "pattern").  If not provided, all types of issues will be ignored for
            the given `target`.

    Examples:
        ```{python}
        import check_datapackage as cdp

        exclude_required = cdp.Exclude(type="required")
        exclude_name = cdp.Exclude(target="$.name")
        exclude_desc_required = cdp.Exclude(
            type="required", target="$.resources[*].description"
        )
        ```
    """

    target: str | None = None
    type: str | None = None
