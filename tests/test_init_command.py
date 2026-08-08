import configparser

from click.testing import CliRunner

from dotify.cli.cli import cli


def test_non_interactive_init_creates_config(tmp_path):
    config_path = tmp_path / "config.ini"
    result = CliRunner().invoke(
        cli,
        [
            "init",
            "--non-interactive",
            "--language",
            "tr",
            "--config-path",
            str(config_path),
        ],
    )

    assert result.exit_code == 0, result.output
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    assert config["dotify"]["language"] == "tr"
    assert "Yapılandırma oluşturuldu" in result.output


def test_non_interactive_init_does_not_overwrite_without_force(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text("[dotify]\nlanguage = en\n", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["init", "--non-interactive", "--config-path", str(config_path)],
    )

    assert result.exit_code != 0
    assert "language = en" in config_path.read_text(encoding="utf-8")
