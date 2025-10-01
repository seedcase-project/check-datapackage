from dataclasses import dataclass


@dataclass(order=True, frozen=True)
class Issue:
    """An issue found while checking a Data Package descriptor.

    One `Issue` object represents one failed check on one field within the descriptor.

    Attributes:
        jsonpath (string): A [JSON path](https://jg-rp.github.io/python-jsonpath/syntax/)
            format pointing to the field in the input object where the issue is located.
            For example, `$.resources[2].name`.
        type (string): The type of the check that failed. Used mostly for excluding
            specific types of issues.
        message (string): A description of what exactly the issue is.

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
