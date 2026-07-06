import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class CheckStatus(Enum):
    """Status of a health check."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    status: CheckStatus
    message: str
    fix: Optional[str] = None
    path: Optional[Path] = None

    def __str__(self) -> str:
        status_symbol = {
            CheckStatus.PASS: "[OK]",
            CheckStatus.FAIL: "[X]",
            CheckStatus.WARN: "[!]",
            CheckStatus.SKIP: "[ ]",
        }
        symbol = status_symbol.get(self.status, "[?]")
        result = f"{symbol} {self.name}: {self.message}"
        if self.path:
            result += f" ({self.path})"
        return result


class HealthCheck:
    """Health check system for Dotify environment."""

    def __init__(self, paths: "DotifyPaths") -> None:
        self.paths = paths
        self.results: list[CheckResult] = []

    def check_all(self, skip_optional: bool = False, cookies_path: Optional[Path] = None) -> list[CheckResult]:
        """Run all health checks."""
        self.results = []

        self.check_config_dir()
        self.check_cookies_file(override_path=cookies_path)
        self.check_wvd_file()
        self.check_ffmpeg()
        self.check_python_version()

        if not skip_optional:
            self.check_optional_binaries()

        return self.results

    def check_config_dir(self) -> CheckResult:
        """Check if config directory exists and is writable."""
        try:
            if not self.paths.config_dir.exists():
                self.paths.config_dir.mkdir(parents=True, exist_ok=True)

            test_file = self.paths.config_dir / ".write_test"
            test_file.touch()
            test_file.unlink()

            result = CheckResult(
                name="Config Directory",
                status=CheckStatus.PASS,
                message="Config directory exists and is writable",
                path=self.paths.config_dir,
            )
        except Exception as e:
            result = CheckResult(
                name="Config Directory",
                status=CheckStatus.FAIL,
                message=f"Config directory error: {str(e)}",
                fix="Check permissions for ~/.dotify directory",
                path=self.paths.config_dir,
            )

        self.results.append(result)
        return result

    def check_cookies_file(self, override_path: Optional[Path] = None) -> CheckResult:
        """Check if cookies file exists."""
        cookies_path = override_path or self.paths.default_cookies_path

        if cookies_path.exists():
            result = CheckResult(
                name="Cookies File",
                status=CheckStatus.PASS,
                message="Cookies file found",
                path=cookies_path,
            )
        else:
            result = CheckResult(
                name="Cookies File",
                status=CheckStatus.FAIL,
                message="Cookies file not found",
                fix=f"Place cookies.txt in {self.paths.config_dir} or use --cookies-path",
                path=cookies_path,
            )

        self.results.append(result)
        return result

    def check_wvd_file(self) -> CheckResult:
        """Check if Widevine key file exists."""
        wvd_path = self.paths.default_wvd_path

        if wvd_path.exists():
            result = CheckResult(
                name="Widevine Key",
                status=CheckStatus.PASS,
                message="Widevine key file found",
                path=wvd_path,
            )
        else:
            result = CheckResult(
                name="Widevine Key",
                status=CheckStatus.WARN,
                message="Widevine key file not found",
                fix=f"Place device.wvd in {self.paths.keys_dir} or use --wvd-path (required for AAC decryption)",
                path=wvd_path,
            )

        self.results.append(result)
        return result

    def check_ffmpeg(self) -> CheckResult:
        """Check if FFmpeg is available."""
        ffmpeg_path = shutil.which("ffmpeg")

        if ffmpeg_path:
            result = CheckResult(
                name="FFmpeg",
                status=CheckStatus.PASS,
                message="FFmpeg found in PATH",
                path=Path(ffmpeg_path),
            )
        else:
            result = CheckResult(
                name="FFmpeg",
                status=CheckStatus.FAIL,
                message="FFmpeg not found in PATH",
                fix="Install FFmpeg and add it to your system PATH",
            )

        self.results.append(result)
        return result

    def check_python_version(self) -> CheckResult:
        """Check if Python version is compatible."""
        import sys

        version = sys.version_info
        if version >= (3, 10):
            result = CheckResult(
                name="Python Version",
                status=CheckStatus.PASS,
                message=f"Python {version.major}.{version.minor}.{version.micro}",
            )
        else:
            result = CheckResult(
                name="Python Version",
                status=CheckStatus.FAIL,
                message=f"Python {version.major}.{version.minor}.{version.micro} (requires 3.10+)",
                fix="Upgrade to Python 3.10 or higher",
            )

        self.results.append(result)
        return result

    def check_optional_binaries(self) -> list[CheckResult]:
        """Check optional binaries."""
        optional_binaries = [
            ("aria2c", "aria2c download mode"),
            ("mp4box", "mp4box remux mode"),
            ("mp4decrypt", "mp4decrypt remux mode"),
            ("packager", "webm video format"),
        ]

        results = []
        for binary, description in optional_binaries:
            binary_path = shutil.which(binary)
            if binary_path:
                result = CheckResult(
                    name=f"Optional: {binary}",
                    status=CheckStatus.PASS,
                    message=f"Found (for {description})",
                    path=Path(binary_path),
                )
            else:
                result = CheckResult(
                    name=f"Optional: {binary}",
                    status=CheckStatus.WARN,
                    message=f"Not found (needed for {description})",
                    fix=f"Install {binary} and add to PATH if needed",
                )
            results.append(result)
            self.results.append(result)

        return results

    def get_failed_checks(self) -> list[CheckResult]:
        """Get all failed checks."""
        return [r for r in self.results if r.status == CheckStatus.FAIL]

    def get_warning_checks(self) -> list[CheckResult]:
        """Get all warning checks."""
        return [r for r in self.results if r.status == CheckStatus.WARN]

    def is_healthy(self) -> bool:
        """Check if all critical checks pass."""
        return not self.get_failed_checks()