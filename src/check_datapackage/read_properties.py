"""Function for reading Data Package properties."""

import json
from pathlib import Path
from typing import Any, cast
from urllib import parse, request
from urllib.error import HTTPError, URLError


class ReadPropertiesError(Exception):
    """Base class for reading Data Package properties errors."""

    pass


class FileDoesNotExistError(ReadPropertiesError):
    """Error when a local path does not point to an existing file."""

    def __init__(self, path: str) -> None:
        """Initialize FileDoesNotExistError with the path."""
        message = (
            f"Could not load '{path}'.\n"
            "The file cannot be found; maybe there is a typo in the path?"
        )
        super().__init__(message)


class JSONFormatError(ReadPropertiesError):
    """Error when a file has invalid JSON format."""

    def __init__(self, path: str, json_error: str) -> None:
        """Initialize JSONFormatError with path and error details."""
        message = (
            f"Could not load '{path}'.\nA JSON formatting issue was found: {json_error}"
        )
        super().__init__(message)


class HTTPStatusError(ReadPropertiesError):
    """Error when an HTTP request returns an error status code."""

    def __init__(self, url: str, code: int, reason: str) -> None:
        """Initialize HTTPStatusError with URL, status code, and reason."""
        message = f"Could not load '{url}'.\nError code {code}: {reason}"
        super().__init__(message)


class HTTPDomainError(ReadPropertiesError):
    """Error when unable to connect to server due to domain not being found."""

    def __init__(self, url: str) -> None:
        """Initialize HTTPDomainError with the URL."""
        message = (
            f"Could not load '{url}'.\n"
            "Couldn't connect to the server because the domain wasn't found."
        )
        super().__init__(message)


class NotJSONError(ReadPropertiesError):
    """Error when a URL does not return JSON content."""

    def __init__(self, url: str, content_type: str) -> None:
        """Initialize NotJSONError with URL and actual content type."""
        message = (
            f"Could not load '{url}'.\nExpected JSON but received '{content_type}'."
        )
        super().__init__(message)


JSON_CONTENT_TYPES = ("application/json", "application/ld+json", "application/geo+json")


def read_properties(path_or_url: str, *, local: bool) -> dict[str, Any]:
    """Read properties from a local or remote Data Package file.

    Args:
        path_or_url: The path or URL to the datapackage.json file.
        local: Whether the source is a local file (True) or remote URL (False).

    Returns:
        The contents of the JSON file as a Python dictionary.

    Raises:
        FileDoesNotExistError: If a local file cannot be found.
        JSONFormatError: If the file cannot be parsed as JSON.
        HTTPStatusError: If an HTTP request returns an error status code.
        HTTPDomainError: If the domain cannot be found.
        NotJSONError: If a URL does not return JSON content.
    """
    if local:
        path = Path(parse.urlsplit(path_or_url).path)
        try:
            with open(path) as properties_file:
                return cast(dict[str, Any], json.load(properties_file))
        except FileNotFoundError:
            raise FileDoesNotExistError(str(path))
        except json.JSONDecodeError as e:
            raise JSONFormatError(str(path), str(e))
    else:
        try:
            with request.urlopen(path_or_url) as open_url:  # nosec B310
                content_type = open_url.headers.get("Content-Type", "")
                if not content_type.startswith(JSON_CONTENT_TYPES + ("text/plain",)):
                    main_type = content_type.split(";")[0].strip()
                    raise NotJSONError(path_or_url, main_type)
                return cast(dict[str, Any], json.load(open_url))
        except HTTPError as e:
            raise HTTPStatusError(path_or_url, e.code, e.reason)
        except URLError as e:
            if "Name or service not known" in str(
                e.reason
            ) or "getaddrinfo failed" in str(e.reason):
                raise HTTPDomainError(path_or_url)
            raise JSONFormatError(path_or_url, str(e))
        except json.JSONDecodeError as e:
            raise JSONFormatError(path_or_url, str(e))
