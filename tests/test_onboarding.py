import configparser
import stat

import pytest

from dotify.env.paths import DotifyPaths
from dotify.onboarding import DotifyInitializer


def test_initializer_writes_cli_compatible_config_atomically(tmp_path):
    paths = DotifyPaths(custom_config_dir=tmp_path / "dotify-home")
    config_path = tmp_path / "custom" / "config.ini"
    initializer = DotifyInitializer(paths, config_path)
    settings = initializer.defaults("tr")

    written = initializer.write(settings)
    config = configparser.ConfigParser(interpolation=None)
    config.read(written, encoding="utf-8")

    assert config["dotify"]["language"] == "tr"
    assert config["dotify"].getboolean("tui") is True
    assert config["dotify"]["output"] == settings.output
    assert stat.S_IMODE(written.stat().st_mode) == 0o600


def test_initializer_preserves_existing_config_without_overwrite(tmp_path):
    paths = DotifyPaths(custom_config_dir=tmp_path / "dotify-home")
    config_path = tmp_path / "config.ini"
    config_path.write_text("[dotify]\nlanguage = en\n", encoding="utf-8")
    initializer = DotifyInitializer(paths, config_path)

    with pytest.raises(FileExistsError):
        initializer.write(initializer.defaults("tr"))

    assert "language = en" in config_path.read_text(encoding="utf-8")
