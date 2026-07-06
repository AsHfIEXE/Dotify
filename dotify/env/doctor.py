import logging
from pathlib import Path
from typing import Optional

from .paths import DotifyPaths
from .checks import HealthCheck, CheckResult, CheckStatus

logger = logging.getLogger(__name__)


class DotifyDoctor:
    """Diagnostic system for Dotify environment."""

    def __init__(self, paths: Optional[DotifyPaths] = None) -> None:
        self.paths = paths or DotifyPaths()
        self.health_check = HealthCheck(self.paths)

    def diagnose(self, verbose: bool = False) -> dict:
        """Run full diagnostic and return results."""
        results = self.health_check.check_all(skip_optional=not verbose)

        diagnosis = {
            "healthy": self.health_check.is_healthy(),
            "results": results,
            "failed": self.health_check.get_failed_checks(),
            "warnings": self.health_check.get_warning_checks(),
            "summary": self._generate_summary(results),
        }

        return diagnosis

    def _generate_summary(self, results: list[CheckResult]) -> str:
        """Generate a human-readable summary."""
        passed = sum(1 for r in results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in results if r.status == CheckStatus.FAIL)
        warnings = sum(1 for r in results if r.status == CheckStatus.WARN)
        skipped = sum(1 for r in results if r.status == CheckStatus.SKIP)

        total = len(results)
        status = "[OK] Healthy" if failed == 0 else "[X] Issues found"

        summary = [
            f"Status: {status}",
            f"Checks: {passed}/{total} passed",
        ]

        if failed > 0:
            summary.append(f"Errors: {failed}")
        if warnings > 0:
            summary.append(f"Warnings: {warnings}")
        if skipped > 0:
            summary.append(f"Skipped: {skipped}")

        return " | ".join(summary)

    def print_diagnosis(self, verbose: bool = False) -> None:
        """Print diagnostic results to console."""
        diagnosis = self.diagnose(verbose)

        print("\n" + "=" * 60)
        print("Dotify Health Check")
        print("=" * 60)
        print(f"\n{diagnosis['summary']}\n")

        for result in diagnosis['results']:
            print(result)
            if result.fix and (result.status == CheckStatus.FAIL or
                              (result.status == CheckStatus.WARN and verbose)):
                print(f"  -> Fix: {result.fix}")

        print("\n" + "=" * 60)

        if diagnosis['failed']:
            print("\n[X] Critical Issues:")
            for result in diagnosis['failed']:
                print(f"  - {result.name}: {result.message}")
                if result.fix:
                    print(f"    Fix: {result.fix}")

        if diagnosis['warnings']:
            print("\n[!] Warnings:")
            for result in diagnosis['warnings']:
                print(f"  - {result.name}: {result.message}")
                if result.fix and verbose:
                    print(f"    Fix: {result.fix}")

        if not diagnosis['failed'] and not diagnosis['warnings']:
            print("\n[OK] All checks passed! Your environment is ready.")

        print("=" * 60 + "\n")

    def get_fix_commands(self) -> list[str]:
        """Get list of fix commands for failed checks."""
        results = self.health_check.check_all()
        failed = [r for r in results if r.status == CheckStatus.FAIL]
        warnings = [r for r in results if r.status == CheckStatus.WARN]

        commands = []

        for result in failed + warnings:
            if result.fix:
                commands.append(f"# {result.name}")
                commands.append(f"# {result.message}")
                commands.append(f"# {result.fix}")
                commands.append("")

        return commands

    def check_specific(self, check_name: str) -> Optional[CheckResult]:
        """Run a specific health check."""
        check_map = {
            "config": self.health_check.check_config_dir,
            "cookies": self.health_check.check_cookies_file,
            "wvd": self.health_check.check_wvd_file,
            "ffmpeg": self.health_check.check_ffmpeg,
            "python": self.health_check.check_python_version,
        }

        check_func = check_map.get(check_name.lower())
        if check_func:
            return check_func()
        return None

    def get_environment_info(self) -> dict:
        """Get detailed environment information."""
        import sys
        import platform

        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "config_dir": str(self.paths.config_dir),
            "config_file": str(self.paths.config_file),
            "keys_dir": str(self.paths.keys_dir),
            "temp_dir": str(self.paths.temp_dir),
            "logs_dir": str(self.paths.logs_dir),
        }