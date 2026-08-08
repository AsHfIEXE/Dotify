from ..utils import DotifyException


class DotifyApiException(DotifyException):
    code = "API_ERROR"


class DotifyRequestException(DotifyApiException):
    def __init__(
        self,
        name: str,
        response_status_code: int,
        response_text: str,
        retry_after: float | None = None,
    ):
        self.code = "RATE_LIMITED" if response_status_code == 429 else "API_REQUEST_FAILED"
        message = f"{name} request failed with status code {response_status_code}: {response_text}"
        if response_status_code == 429:
            message += "\n\nSpotify rate-limited this request."
            if retry_after is not None:
                message += f" Retry after {retry_after:g} seconds."
            else:
                message += " Stop retrying and wait at least 60 seconds."
            message += (
                "\nDo not run concurrent Dotify processes; immediate retries "
                "can extend the cooldown."
            )
        elif response_status_code == 401:
            message += "\n\nThis usually means your cookies are expired or invalid."
            message += "\nTo fix: Export fresh cookies from open.spotify.com and run 'dotify env doctor'"
        elif response_status_code == 403:
            message += "\n\nAccess denied. Your account may not have the required permissions."
            message += "\nTo fix: Check your account type and run 'dotify env doctor'"
        elif response_status_code == 404:
            message += "\n\nResource not found. The URL may be invalid or the content was removed."
        elif response_status_code >= 500:
            message += "\n\nSpotify server error. Please try again later."

        super().__init__(message)
        self.response_status_code = response_status_code
        self.response_text = response_text
        self.retry_after = retry_after


class DotifyAuthenticationException(DotifyApiException):
    code = "AUTH_FAILED"

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            f"{message}\n\n"
            "To fix:\n"
            "1. Export fresh cookies from open.spotify.com\n"
            "2. Ensure you're logged in to your Spotify account\n"
            "3. Replace the old cookies.txt with the new one\n"
            "4. Run 'dotify env doctor' to verify"
        )


class DotifyBrowserCookieException(DotifyApiException):
    """A local browser cookie store could not provide Spotify authentication."""

    code = "BROWSER_COOKIE_IMPORT_FAILED"


class DotifyLibrespotAuthenticationException(DotifyApiException):
    """Librespot-specific authentication failure with actionable guidance."""

    code = "LIBRESPOT_AUTH_FAILED"

    def __init__(self, message: str):
        super().__init__(
            f"{message}\n\n"
            "To fix:\n"
            "1. Run 'dotify auth librespot' to authorize Librespot\n"
            "2. Complete the Spotify login in your browser\n"
            "3. Retry with --session-type librespot\n\n"
            "Dotify will not silently fall back to the Web session."
        )


class DotifyLibrespotConnectionException(DotifyApiException):
    """Librespot could not reach a Spotify access point."""

    code = "LIBRESPOT_CONNECTION_FAILED"

    def __init__(self, message: str):
        super().__init__(
            f"{message}\n\n"
            "The stored Librespot credentials were not rejected. This is a "
            "connection or Spotify access-point failure; retry after checking "
            "your network connection."
        )


class DotifyPremiumRequiredException(DotifyApiException):
    code = "PREMIUM_REQUIRED"

    def __init__(self):
        super().__init__(
            "Premium account required for this feature.\n\n"
            "To fix:\n"
            "1. Upgrade to Spotify Premium\n"
            "2. Select a non-Premium fallback such as aac-medium or "
            "vorbis-medium when supported by the selected session"
        )
