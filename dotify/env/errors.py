import logging
from http.cookiejar import LoadError
from typing import Optional

from ..api.exceptions import (
    DotifyAuthenticationException,
    DotifyBrowserCookieException,
    DotifyLibrespotAuthenticationException,
    DotifyLibrespotConnectionException,
    DotifyPremiumRequiredException,
    DotifyRequestException,
)
from ..downloader.exceptions import (
    DotifyDependencyNotFound,
    DotifyDownloadError,
    DotifyFFmpegError,
    DotifyMediaFileExists,
    DotifySyncedLyricsOnly,
    DotifyWidevineError,
)
from ..interface.exceptions import (
    DotifyLibrespotAudioKeyException,
    DotifyMediaException,
    DotifyMediaFlatFilterException,
    DotifyMediaFormatNotAvailableException,
    DotifyMediaFormatNotAvailableForSessionTypeException,
    DotifyMediaNotFoundException,
    DotifyMediaUnstreamableException,
    DotifyNoCdmException,
    DotifyNoKeyEmuException,
    DotifyUnsupportedMediaTypeException,
    DotifyUrlParseException,
)
from .paths import DotifyPaths
from .checks import HealthCheck, CheckStatus

logger = logging.getLogger(__name__)


class DotifyErrorHandler:
    """Enhanced error handler with helpful messages and fix suggestions."""

    def __init__(self, paths: Optional[DotifyPaths] = None, language: str = "en") -> None:
        self.paths = paths or DotifyPaths()
        self.language = language
        self.health_check = HealthCheck(self.paths)

    def handle_missing_cookies(self) -> str:
        """Handle missing cookies file error."""
        return (
            "Cookies file not found or invalid.\n"
            f"Expected location: {self.paths.default_cookies_path}\n"
            f"Or use --cookies-path to specify a different location.\n\n"
            "To fix:\n"
            "1. Install 'Get cookies.txt LOCALLY' extension\n"
            "2. Go to open.spotify.com and log in\n"
            "3. Export cookies to cookies.txt\n"
            "4. Place the file in ~/.dotify/ or use --cookies-path\n"
            "5. Run 'dotify env doctor' to verify"
        )

    def handle_missing_wvd(self) -> str:
        """Handle missing Widevine key error."""
        return (
            "Widevine key file not found.\n"
            f"Expected location: {self.paths.default_wvd_path}\n"
            f"Or use --wvd-path to specify a different location.\n\n"
            "To fix:\n"
            "1. Use KeyDive on an Android device\n"
            "2. Extract the device.wvd file\n"
            "3. Place it in ~/.dotify/keys/ or use --wvd-path\n"
            "4. Run 'dotify env doctor' to verify\n\n"
            "Note: WVD is required for protected AAC/MP4-FLAC and video streams. "
            "The web session uses protected AAC/MP4 streams. To use Vorbis "
            "without WVD, install the librespot extra and run with "
            "--session-type librespot --audio-quality vorbis-medium."
        )

    def handle_missing_ffmpeg(self) -> str:
        """Handle missing FFmpeg error."""
        return (
            "FFmpeg not found in PATH.\n\n"
            "To fix:\n"
            "Windows: Download from https://www.animemusic.info/2024/02/ffmpeg-builds-static-shared.html\n"
            "Linux: Download from https://johnvansickle.com/ffmpeg/\n"
            "Add FFmpeg to your system PATH and restart.\n"
            "Run 'dotify env doctor' to verify."
        )

    def handle_missing_binary(self, binary_name: str, purpose: str) -> str:
        """Handle missing optional binary error."""
        return (
            f"{binary_name} not found in PATH.\n"
            f"Required for: {purpose}\n\n"
            f"To fix:\n"
            f"Install {binary_name} and add it to your system PATH.\n"
            f"Run 'dotify env doctor --verbose' to check all dependencies."
        )

    def handle_authentication_error(self) -> str:
        """Handle authentication error."""
        return (
            "Authentication failed. Your cookies may be expired or invalid.\n\n"
            "To fix:\n"
            "1. Export fresh cookies from open.spotify.com\n"
            "2. Ensure you're logged in to your Spotify account\n"
            "3. Replace the old cookies.txt with the new one\n"
            "4. Run 'dotify env doctor' to verify"
        )

    def handle_premium_required(self) -> str:
        """Handle premium account required error."""
        return (
            "Premium account required for this feature.\n\n"
            "To fix:\n"
            "1. Upgrade to Spotify Premium\n"
            "2. Select a non-Premium fallback such as aac-medium or "
            "vorbis-medium when supported by the selected session"
        )

    def handle_download_error(self, error: Exception) -> str:
        """Handle general download error."""
        message = self._handle_download_error(error)
        if self.language == "tr":
            message = self._translate_error(error, message)
        code = getattr(error, "code", "UNEXPECTED_ERROR")
        return f"[{code}] {message}"

    def _handle_download_error(self, error: Exception) -> str:
        if isinstance(
            error,
            (FileNotFoundError, LoadError, DotifyAuthenticationException),
        ):
            return self.handle_missing_cookies()
        if isinstance(error, DotifyNoCdmException):
            return self.handle_missing_wvd()
        if isinstance(error, DotifyDependencyNotFound):
            if error.dependency.lower() == "ffmpeg":
                return self.handle_missing_ffmpeg()
            return self.handle_missing_binary(
                error.dependency,
                "the selected download or remux mode",
            )
        if isinstance(error, DotifyPremiumRequiredException):
            return self.handle_premium_required()
        if isinstance(
            error,
            (
                DotifyLibrespotAuthenticationException,
                DotifyBrowserCookieException,
                DotifyLibrespotConnectionException,
                DotifyLibrespotAudioKeyException,
                DotifyDownloadError,
                DotifyFFmpegError,
                DotifyRequestException,
                DotifyWidevineError,
            ),
        ):
            return str(error)

        details = str(error).strip() or type(error).__name__
        return (
            f"Download error: {details}\n\n"
            "Run 'dotify env doctor' to check your environment setup."
        )

    @staticmethod
    def _translate_error(error: Exception, fallback: str) -> str:
        if isinstance(error, DotifyRequestException):
            if error.response_status_code == 429:
                wait = (
                    f"{error.retry_after:g} saniye bekleyin."
                    if error.retry_after is not None
                    else "En az 60 saniye bekleyin."
                )
                return (
                    f"Spotify isteği hız sınırına takıldı (429). {wait}\n"
                    "Aynı anda birden fazla Dotify süreci çalıştırmayın."
                )
            return (
                f"Spotify isteği başarısız oldu: HTTP {error.response_status_code}. "
                f"{error.response_text}"
            ).strip()
        if isinstance(error, DotifyBrowserCookieException):
            return (
                "Tarayıcıda giriş yapılmış bir Spotify sp_dc çerezi bulunamadı. "
                "Spotify Web'i seçilen tarayıcıda açıp giriş yapın; ardından komutu "
                "yeniden çalıştırın. macOS anahtar zinciri veya disk erişimi isterse "
                "izin vermeniz gerekebilir."
            )
        if isinstance(error, DotifyLibrespotConnectionException):
            return (
                "Librespot Spotify erişim noktasına bağlanamadı. Kimlik bilgileri "
                "reddedilmedi; ağ bağlantınızı kontrol edip yeniden deneyin."
            )
        if isinstance(error, DotifyLibrespotAuthenticationException):
            return (
                "Librespot kimlik doğrulaması başarısız. "
                "'dotify auth librespot --force' çalıştırıp yeniden deneyin."
            )
        if isinstance(error, DotifyLibrespotAudioKeyException):
            return (
                "Spotify Librespot ses anahtarını reddetti. Dotify önce alternatif "
                "Librespot dosyalarını, gerekirse WVD ile Web akışını dener."
            )
        if isinstance(error, DotifyNoCdmException):
            return "Bu içerik için geçerli bir device.wvd dosyası gerekiyor."
        if isinstance(error, DotifyDependencyNotFound):
            return f"Gerekli bağımlılık bulunamadı: {error.dependency}."
        if isinstance(error, DotifyPremiumRequiredException):
            return "Bu özellik için Spotify Premium hesabı gerekiyor."
        if isinstance(error, DotifyMediaFileExists):
            return f"Medya dosyası zaten mevcut: {error.media_path}"
        if isinstance(error, DotifySyncedLyricsOnly):
            return "Yalnızca senkronize şarkı sözü işlemi tamamlandı."
        if isinstance(error, DotifyUrlParseException):
            return f"Spotify URL'si çözümlenemedi: {error.url}"
        if isinstance(error, DotifyUnsupportedMediaTypeException):
            return f"Desteklenmeyen Spotify içerik türü: {error.media_type}"
        if isinstance(error, DotifyMediaFlatFilterException):
            return f"Medya filtre tarafından atlandı: {error.media_id}"
        if isinstance(error, DotifyMediaNotFoundException):
            return f"Medya bulunamadı: {error.media_id}"
        if isinstance(error, DotifyMediaUnstreamableException):
            return f"Medya oynatılamıyor: {error.media_id}"
        if isinstance(
            error,
            (
                DotifyMediaFormatNotAvailableException,
                DotifyMediaFormatNotAvailableForSessionTypeException,
            ),
        ):
            return f"Seçilen biçim bu oturumda kullanılamıyor: {error.media_id}"
        if isinstance(error, DotifyMediaException):
            return f"Spotify medya hatası: {error.media_id}"
        if isinstance(error, DotifyNoKeyEmuException):
            return "Bu içerik için geçerli bir Spotify DLL anahtar emülatörü gerekiyor."
        if isinstance(error, DotifyFFmpegError):
            return "FFmpeg işlemi başarısız. 'dotify env doctor' ile kurulumu denetleyin."
        if isinstance(error, DotifyWidevineError):
            return "Widevine çözme işlemi başarısız. WVD dosyasını ve hesabı denetleyin."
        if isinstance(error, DotifyDownloadError):
            result = f"İndirme başarısız: {error.message}"
            if error.url:
                result += f"\nURL: {error.url}"
            return result + "\n\nOrtamı denetlemek için 'dotify env doctor' çalıştırın."
        if isinstance(error, (FileNotFoundError, LoadError, DotifyAuthenticationException)):
            return (
                "Spotify cookie dosyası bulunamadı veya geçersiz. Güncel cookies.txt "
                "dosyasını --cookies-path ile belirtin."
            )
        details = str(error).strip()
        if details:
            return f"Beklenmeyen hata: {details}"
        return fallback

    def get_suggestion(self, error_type: str) -> str:
        """Get a suggestion for a specific error type."""
        suggestions = {
            "cookies": self.handle_missing_cookies(),
            "wvd": self.handle_missing_wvd(),
            "ffmpeg": self.handle_missing_ffmpeg(),
            "auth": self.handle_authentication_error(),
        }
        return suggestions.get(
            error_type,
            "Run 'dotify env doctor' for diagnostics.",
        )

    def log_error_with_fix(self, error: Exception, context: str = "") -> None:
        """Log an error with helpful fix suggestion."""
        prefix = f"{context}: " if context else ""
        logger.error(prefix + self.handle_download_error(error))
