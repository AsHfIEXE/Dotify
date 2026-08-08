"""First-run configuration service used by ``dotify init``."""

from __future__ import annotations

import configparser
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from InquirerPy import inquirer
from InquirerPy.base.control import Choice

from .env.paths import DotifyPaths
from .i18n import Translator, detect_language


QUALITY_PROFILES: dict[str, str] = {
    "balanced": "vorbis-high,aac-medium",
    "compatible": "aac-medium",
    "lossless": "flac-flac-24,flac-flac,aac-high",
}


@dataclass(frozen=True, slots=True)
class InitSettings:
    language: str
    output: str
    temp: str
    cookies_path: str
    wvd_path: str | None
    audio_quality: str
    tui: bool
    wait_interval: int

    def as_config(self) -> dict[str, str]:
        return {
            "language": self.language,
            "output": self.output,
            "temp": self.temp,
            "cookies_path": self.cookies_path,
            "wvd_path": self.wvd_path or "null",
            "audio_quality": self.audio_quality,
            "tui": "true" if self.tui else "false",
            "wait_interval": str(max(0, self.wait_interval)),
        }


class DotifyInitializer:
    def __init__(
        self,
        paths: DotifyPaths | None = None,
        config_path: Path | None = None,
    ) -> None:
        self.paths = paths or DotifyPaths()
        self.config_path = config_path or self.paths.config_file

    def defaults(self, language: str = "auto") -> InitSettings:
        return InitSettings(
            language=detect_language(language),
            output=str(Path.cwd() / "Spotify"),
            temp=str(self.paths.temp_dir),
            cookies_path=str(self.paths.default_cookies_path),
            wvd_path=str(self.paths.default_wvd_path),
            audio_quality=QUALITY_PROFILES["balanced"],
            tui=True,
            wait_interval=1,
        )

    async def prompt(self, language: str | None = None) -> InitSettings:
        selected_language = language
        if not selected_language or selected_language == "auto":
            selected_language = await inquirer.select(
                message="Language / Dil:",
                choices=[
                    Choice("en", "English"),
                    Choice("tr", "Türkçe"),
                ],
                default=detect_language(),
            ).execute_async()

        translator = Translator(selected_language)
        defaults = self.defaults(selected_language)
        output = await inquirer.filepath(
            message=translator("init_output"),
            default=defaults.output,
        ).execute_async()
        quality_profile = await inquirer.select(
            message=translator("init_quality"),
            choices=[
                Choice("balanced", translator("quality_balanced")),
                Choice("compatible", translator("quality_compatible")),
                Choice("lossless", translator("quality_lossless")),
            ],
            default="balanced",
        ).execute_async()
        cookies_path = await inquirer.filepath(
            message=translator("init_cookies"),
            default=defaults.cookies_path,
        ).execute_async()
        wvd_path = await inquirer.text(
            message=translator("init_wvd"),
            default=defaults.wvd_path or "",
        ).execute_async()
        tui = await inquirer.confirm(
            message=translator("init_tui"),
            default=True,
        ).execute_async()
        wait_interval = await inquirer.number(
            message=translator("init_wait"),
            default=defaults.wait_interval,
            min_allowed=0,
        ).execute_async()

        return InitSettings(
            language=selected_language,
            output=str(Path(output).expanduser()),
            temp=defaults.temp,
            cookies_path=str(Path(cookies_path).expanduser()),
            wvd_path=str(Path(wvd_path).expanduser()) if wvd_path else None,
            audio_quality=QUALITY_PROFILES[quality_profile],
            tui=tui,
            wait_interval=int(wait_interval),
        )

    def write(self, settings: InitSettings, overwrite: bool = False) -> Path:
        if self.config_path.exists() and not overwrite:
            raise FileExistsError(self.config_path)

        config = configparser.ConfigParser(interpolation=None)
        config["dotify"] = settings.as_config()
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.config_path.parent,
                prefix=".config-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                config.write(temporary)
                temporary_name = temporary.name
            os.chmod(temporary_name, 0o600)
            Path(temporary_name).replace(self.config_path)
        finally:
            if temporary_name and Path(temporary_name).exists():
                Path(temporary_name).unlink()

        return self.config_path

