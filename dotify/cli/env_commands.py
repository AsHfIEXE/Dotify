import logging
import click

from ..env.paths import DotifyPaths
from ..env.setup import DotifySetup
from ..env.doctor import DotifyDoctor

logger = logging.getLogger(__name__)


@click.group()
def env():
    """Environment management commands."""
    pass


@env.command()
@click.option(
    "--skip-sensitive",
    is_flag=True,
    default=True,
    help="Skip setup of sensitive files (cookies, wvd)",
)
@click.option(
    "--create-placeholders",
    is_flag=True,
    default=False,
    help="Create placeholder files for sensitive data",
)
def setup(skip_sensitive: bool, create_placeholders: bool):
    """Set up Dotify environment automatically."""
    colorama = __import__("colorama")
    colorama.just_fix_windows_console()

    paths = DotifyPaths()
    setup_manager = DotifySetup(paths)

    click.echo("\n[Setup] Setting up Dotify environment...\n")

    success = setup_manager.setup_all(skip_sensitive=skip_sensitive)

    if create_placeholders:
        click.echo("\n[Setup] Creating placeholder files...")
        setup_manager.create_placeholder_files()

    if success:
        click.echo("\n[OK] Setup completed successfully!")
        click.echo("\nNext steps:")
        click.echo(f"  1. Place cookies.txt in: {paths.config_dir}")
        click.echo(f"  2. Place device.wvd in: {paths.keys_dir}")
        click.echo("  3. Run 'dotify env doctor' to verify your setup")
    else:
        click.echo("\n[WARN] Setup completed with some issues.")
        click.echo("Run 'dotify env doctor' to see details.")


@env.command()
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show detailed output including optional checks",
)
@click.option(
    "--json",
    is_flag=True,
    default=False,
    help="Output results in JSON format",
)
def doctor(verbose: bool, json: bool):
    """Check system health and diagnose issues."""
    colorama = __import__("colorama")
    colorama.just_fix_windows_console()

    paths = DotifyPaths()
    doctor = DotifyDoctor(paths)

    if json:
        import json

        diagnosis = doctor.diagnose(verbose=verbose)
        output = {
            "healthy": diagnosis["healthy"],
            "summary": diagnosis["summary"],
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "message": r.message,
                    "fix": r.fix,
                    "path": str(r.path) if r.path else None,
                }
                for r in diagnosis["results"]
            ],
        }
        click.echo(json.dumps(output, indent=2))
    else:
        doctor.print_diagnosis(verbose=verbose)


@env.command()
def paths():
    """Show all Dotify paths."""
    colorama = __import__("colorama")
    colorama.just_fix_windows_console()

    paths = DotifyPaths()

    click.echo("\n[Paths] Dotify Paths:\n")
    click.echo(f"Config Directory: {paths.config_dir}")
    click.echo(f"Config File:      {paths.config_file}")
    click.echo(f"Keys Directory:   {paths.keys_dir}")
    click.echo(f"Temp Directory:  {paths.temp_dir}")
    click.echo(f"Logs Directory:   {paths.logs_dir}")
    click.echo(f"Database File:    {paths.database_file}")
    click.echo(f"\nDefault Paths:")
    click.echo(f"Cookies:          {paths.default_cookies_path}")
    click.echo(f"Widevine Key:     {paths.default_wvd_path}")
    click.echo()


@env.command()
@click.argument("check_name", required=False)
def check(check_name: str):
    """Run a specific health check."""
    colorama = __import__("colorama")
    colorama.just_fix_windows_console()

    paths = DotifyPaths()
    doctor = DotifyDoctor(paths)

    if check_name:
        result = doctor.check_specific(check_name)
        if result:
            click.echo(f"\n{result}\n")
            if result.fix:
                click.echo(f"Fix: {result.fix}\n")
        else:
            click.echo(f"\n❌ Unknown check: {check_name}")
            click.echo("Available checks: config, cookies, wvd, ffmpeg, python\n")
    else:
        doctor.print_diagnosis(verbose=False)