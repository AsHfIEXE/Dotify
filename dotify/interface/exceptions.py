from typing import Any

from ..api.enums import SessionType
from ..utils import DotifyException


class DotifyInterfaceException(DotifyException):
    pass


class DotifyNoCdmException(DotifyInterfaceException):
    def __init__(self):
        super().__init__("Content requires a CDM but no .wvd file was provided")


class DotifyNoKeyEmuException(DotifyInterfaceException):
    def __init__(self):
        super().__init__(
            "Content requires decryption but no Spotify DLL file was provided"
        )


class DotifyUrlParseException(DotifyInterfaceException):
    def __init__(self, url: str):
        super().__init__(f"Failed to parse Spotify URL: {url}")

        self.url = url


class DotifyUnsupportedMediaTypeException(DotifyInterfaceException):
    def __init__(self, media_type: str):
        super().__init__(f"Unsupported URL media type: {media_type}")

        self.media_type = media_type


class DotifyMediaException(DotifyInterfaceException):
    def __init__(self, message: str, media_id: str):
        super().__init__(f"{message}: {media_id}")

        self.media_id = media_id


class DotifyMediaFlatFilterException(DotifyMediaException):
    def __init__(
        self,
        media_id: str,
        result: Any = None,
    ):
        super().__init__(
            "Media filtered out by flat filter",
            media_id=media_id,
        )

        self.result = result


class DotifyMediaNotFoundException(DotifyMediaException):
    def __init__(self, media_id: str):
        super().__init__(
            "Media not found",
            media_id=media_id,
        )


class DotifyMediaUnstreamableException(DotifyMediaException):
    def __init__(self, media_id: str):
        super().__init__(
            "Media is not streamable",
            media_id=media_id,
        )


class DotifyMediaFormatNotAvailableException(DotifyMediaException):
    def __init__(
        self,
        media_id: str,
    ):
        super().__init__(
            "Selected format is not available",
            media_id=media_id,
        )


class DotifyMediaFormatNotAvailableForSessionTypeException(DotifyMediaException):
    def __init__(
        self,
        media_id: str,
        session_type: SessionType | None = None,
    ):
        message = "Selected format is not available for session type"
        if session_type:
            message += f": {session_type.value}"

        super().__init__(
            media_id=media_id,
            message=message,
        )
