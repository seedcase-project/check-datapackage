import re
from dataclasses import dataclass

from check_datapackage.check_error import CheckError


@dataclass
class CheckErrorMatcher:
    r"""A class that helps to filter `CheckError`s based on their attributes.

    Examples:
            ```{python}
            error = CheckError(
                message="123 is not of type 'string'",
                json_path="$.resources[0].name",
                validator="type",
            )
            matcher = CheckErrorMatcher(
                message="of type 'string'",
                json_path=r"resources\[.\]",
                validator="type",
            )
            matcher.matches(error)

            ```
    """

    # The substring to find in the error message.
    message: str | None = None
    # The subpath to find in the error's `json_path`. Expressed as a regular expression.
    json_path: str | None = None
    # The validator to match.
    validator: str | None = None

    def matches(self, error: CheckError) -> bool:
        """Determines if this matcher matches the given `CheckError`.

        Args:
            error: The `CheckError` to match.

        Returns:
            If there was a match.
        """
        return (
            self.message_matches(error)
            and self.json_path_matches(error)
            and self.validator_matches(error)
        )

    def message_matches(self, error: CheckError) -> bool:
        """Determines if this matcher matches the message of the given `CheckError`.

        Args:
            error: The `CheckError` to match.

        Returns:
            If there was a match.
        """
        return self.message is None or self.message in error.message

    def json_path_matches(self, error: CheckError) -> bool:
        """Determines if this matcher matches the `json_path` of the given `CheckError`.

        Matching regular expressions is supported.

        Args:
            error: The `CheckError` to match.

        Returns:
            If there was a match.
        """
        if self.json_path is None:
            return True
        return re.search(self.json_path, error.json_path) is not None

    def validator_matches(self, error: CheckError) -> bool:
        """Determines if this matcher matches the validator of the given `CheckError`.

        Args:
            error: The `CheckError` to match.

        Returns:
            If there was a match.
        """
        return self.validator is None or self.validator == error.validator
