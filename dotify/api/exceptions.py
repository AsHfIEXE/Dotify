from ..utils import DotifyException


class DotifyApiException(DotifyException):
    pass


class DotifyRequestException(DotifyApiException):
    def __init__(
        self,
        name: str,
        response_status_code: int,
        response_text: str,
    ):
        message = f"{name} request failed with status code {response_status_code}: {response_text}"
        if response_status_code == 401:
            message += "\n\nThis usually means your cookies are expired or invalid."
            message += "\nTo fix: Export fresh cookies from open.spotify.com and run 'dotify doctor'"
        elif response_status_code == 403:
            message += "\n\nAccess denied. Your account may not have the required permissions."
            message += "\nTo fix: Check your account type and run 'dotify doctor'"
        elif response_status_code == 404:
            message += "\n\nResource not found. The URL may be invalid or the content was removed."
        elif response_status_code >= 500:
            message += "\n\nSpotify server error. Please try again later."

        super().__init__(message)
        self.response_status_code = response_status_code
        self.response_text = response_text


class DotifyAuthenticationException(DotifyApiException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            f"{message}\n\n"
            "To fix:\n"
            "1. Export fresh cookies from open.spotify.com\n"
            "2. Ensure you're logged in to your Spotify account\n"
            "3. Replace the old cookies.txt with the new one\n"
            "4. Run 'dotify doctor' to verify"
        )


class DotifyPremiumRequiredException(DotifyApiException):
    def __init__(self):
        super().__init__(
            "Premium account required for this feature.\n\n"
            "To fix:\n"
            "1. Upgrade to Spotify Premium\n"
            "2. Use --force-premium to bypass this check (may not work)\n"
            "3. Or use --disable-wvd to download in Vorbis format instead"
        )
