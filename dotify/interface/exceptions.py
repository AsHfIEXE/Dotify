from typing import Any

from ..api.enums import SessionType
from ..utils import DotifyException


class DotifyInterfaceException(DotifyException):
    code = "INTERFACE_ERROR"


class DotifyNoCdmException(DotifyInterfaceException):
    code = "WVD_REQUIRED"

    def __init__(self):
        super().__init__("Content requires a CDM but no .wvd file was provided")


class DotifyNoKeyEmuException(DotifyInterfaceException):
    code = "SPOTIFY_DLL_REQUIRED"

    def __init__(self):
        super().__init__(
            "Content requires decryption but no Spotify DLL file was provided"
        )


class DotifyLibrespotAudioKeyException(DotifyInterfaceException):
    code = "LIBRESPOT_AUDIO_KEY_REJECTED"

    def __init__(self, media_id: str, file_id: bytes):
        super().__init__(
            "Spotify rejected the Librespot audio key request (code 1). "
            "This is a known Spotify-side issue that can affect OAuth-based "
            "Librespot sessions on some Premium accounts.\n\n"
            f"Media ID: {media_id}\n"
            f"File ID: {file_id.hex()}\n\n"
            "If a WVD is configured, Dotify can fall back to the protected "
            "AAC/Web stream. Otherwise retry with --session-type web after "
            "configuring --wvd-path."
        )

        self.media_id = media_id
        self.file_id = file_id


class DotifyUrlParseException(DotifyInterfaceException):
    code = "INVALID_SPOTIFY_URL"

    def __init__(self, url: str):
        super().__init__(f"Failed to parse Spotify URL: {url}")

        self.url = url


class DotifyUnsupportedMediaTypeException(DotifyInterfaceException):
    code = "UNSUPPORTED_MEDIA"

    def __init__(self, media_type: str):
        super().__init__(f"Unsupported URL media type: {media_type}")

        self.media_type = media_type


class DotifyMediaException(DotifyInterfaceException):
    code = "MEDIA_ERROR"

    def __init__(self, message: str, media_id: str):
        super().__init__(f"{message}: {media_id}")

        self.media_id = media_id


class DotifyMediaFlatFilterException(DotifyMediaException):
    code = "FILTERED_OUT"

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
    code = "MEDIA_NOT_FOUND"

    def __init__(self, media_id: str):
        super().__init__(
            "Media not found",
            media_id=media_id,
        )


class DotifyMediaUnstreamableException(DotifyMediaException):
    code = "MEDIA_UNSTREAMABLE"

    def __init__(self, media_id: str):
        super().__init__(
            "Media is not streamable",
            media_id=media_id,
        )


class DotifyMediaFormatNotAvailableException(DotifyMediaException):
    code = "FORMAT_UNAVAILABLE"

    def __init__(
        self,
        media_id: str,
    ):
        super().__init__(
            "Selected format is not available",
            media_id=media_id,
        )


class DotifyMediaFormatNotAvailableForSessionTypeException(DotifyMediaException):
    code = "FORMAT_UNAVAILABLE_FOR_SESSION"

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
