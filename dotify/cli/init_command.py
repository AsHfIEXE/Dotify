from __future__ import annotations

from pathlib import Path

import click
from InquirerPy import inquirer

from ..env.paths import DotifyPaths
from ..i18n import SUPPORTED_LANGUAGES, Translator, detect_language
from ..onboarding import DotifyInitializer


@click.command("init")
@click.option(
    "--language",
    type=click.Choice(["auto", *SUPPORTED_LANGUAGES]),
    default="auto",
    show_default=True,
)
@click.option(
    "--config-path",
    type=click.Path(path_type=Path, dir_okay=False, writable=True),
    default=None,
)
@click.option("--non-interactive", is_flag=True, help="Accept recommended defaults.")
@click.option("--force", is_flag=True, help="Overwrite an existing configuration.")
def init_command(
    language: str,
    config_path: Path | None,
    non_interactive: bool,
    force: bool,
) -> None:
    """Run the first-time setup wizard."""

    paths = DotifyPaths()
    initializer = DotifyInitializer(paths, config_path=config_path)
    selected_language = detect_language(language)
    translator = Translator(selected_language)
    click.echo(f"\n{translator('init_title')}\n")

    if initializer.config_path.exists() and not force:
        if non_interactive:
            raise click.ClickException(
                translator("init_exists", path=initializer.config_path)
            )
        overwrite = inquirer.confirm(
            message=translator("init_exists", path=initializer.config_path),
            default=False,
        ).execute()
        if not overwrite:
            click.echo(translator("init_cancelled"))
            return
        force = True

    settings = (
        initializer.defaults(selected_language)
        if non_interactive
        else __import__("asyncio").run(initializer.prompt(language))
    )
    written_path = initializer.write(settings, overwrite=force)
    click.echo(translator("init_complete", path=written_path))
    click.echo(translator("init_next"))

