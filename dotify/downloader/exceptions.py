from ..utils import DotifyException


class DotifyDownloaderException(DotifyException):
    pass


class DotifyMediaFileExists(DotifyDownloaderException):
    def __init__(self, media_path: str):
        super().__init__(f"Media file already exists at path: {media_path}")

        self.media_path = media_path


class DotifyDependencyNotFound(DotifyDownloaderException):
    def __init__(self, dependency: str, fix: str = None):
        message = f"Dependency not found: {dependency}"
        if fix:
            message += f"\n\nFix: {fix}"
        super().__init__(message)

        self.dependency = dependency
        self.fix = fix


class DotifySyncedLyricsOnly(DotifyDownloaderException):
    def __init__(self):
        super().__init__("Only downloading synced lyrics is supported")


class DotifyWidevineError(DotifyDownloaderException):
    def __init__(self, message: str = "Widevine decryption failed"):
        super().__init__(
            f"{message}\n\n"
            "This usually means:\n"
            "1. Your device.wvd file is invalid or expired\n"
            "2. The content requires a different device key\n"
            "3. Your account doesn't have premium access\n\n"
            "To fix:\n"
            "1. Run 'dotify doctor' to check your WVD file\n"
            "2. Try extracting a new WVD file with KeyDive\n"
            "3. Use --disable-wvd to download in Vorbis format instead"
        )


class DotifyFFmpegError(DotifyDownloaderException):
    def __init__(self, message: str = "FFmpeg processing failed"):
        super().__init__(
            f"{message}\n\n"
            "To fix:\n"
            "1. Ensure FFmpeg is installed and in PATH\n"
            "2. Run 'dotify doctor' to verify FFmpeg installation\n"
            "3. Check that FFmpeg version supports required codecs"
        )


class DotifyDownloadError(DotifyDownloaderException):
    def __init__(self, message: str, url: str = None):
        full_message = f"Download failed: {message}"
        if url:
            full_message += f"\nURL: {url}"
        full_message += "\n\nRun 'dotify doctor' to check your environment"
        super().__init__(full_message)

        self.url = url
