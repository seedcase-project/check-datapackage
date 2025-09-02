from functools import total_ordering


@total_ordering
class CheckError(Exception):
    """Raised or returned when a properties object fails a single check."""

    def __init__(
        self,
        message: str,
        json_path: str,
        validator: str,
    ):
        """Initialises CheckError.

        Args:
            message: The error message.
            json_path: The path to the JSON field within the enclosing JSON object where
                the error occurred.
            validator: The name of the validator that failed.
        """
        self.message = message
        self.json_path = json_path
        self.validator = validator
        super().__init__(self.__str__())

    def __eq__(self, other: object) -> bool:
        """Checks if this error is equal to an object.

        Args:
            other: The object to compare.

        Returns:
            If the objects are equal.
        """
        if not isinstance(other, CheckError):
            return NotImplemented
        return (
            self.message == other.message
            and self.json_path == other.json_path
            and self.validator == other.validator
        )

    def __lt__(self, other: object) -> bool:
        """Checks if this error is less than an object.

        Args:
            other: The object to compare.

        Returns:
            The result of the comparison.
        """
        if not isinstance(other, CheckError):
            return NotImplemented
        return (self.json_path, self.validator, self.message) < (
            other.json_path,
            other.validator,
            other.message,
        )

    def __hash__(self) -> int:
        """Returns a hash for this error.

        Returns:
            The hash.
        """
        return hash((self.message, self.json_path, self.validator))

    def __str__(self) -> str:
        """Returns a user-friendly string representation of the error.

        Returns:
            The string representation.
        """
        return (
            f"Error at `{self.json_path}` caused by `{self.validator}`: {self.message}"
        )

    def __repr__(self) -> str:
        """Returns a developer-friendly, unambiguous representation of the error.

        Returns:
            The developer-friendly representation.
        """
        return (
            f"CheckError(message={self.message!r}, "
            f"json_path={self.json_path!r}, "
            f"validator={self.validator!r})"
        )
