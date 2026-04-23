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
        super().__init__(
            f"{name} request failed with status code {response_status_code}: {response_text}"
        )
        self.response_status_code = response_status_code
        self.response_text = response_text
