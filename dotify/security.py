"""Cross-platform protection for files that contain authentication material."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def restrict_file_to_current_user(path: str | Path) -> None:
    """Limit a sensitive file to the current user.

    POSIX permissions express this directly with ``0600``. Windows instead
    uses ACLs, so ``chmod`` cannot provide the same guarantee there. Removing
    inherited ACL entries and granting full control only to the signed-in user
    keeps future credential updates and deletions possible while withholding
    access from other local accounts.
    """

    file_path = Path(path)
    if os.name != "nt":
        os.chmod(file_path, 0o600)
        return

    username = os.environ.get("USERNAME")
    if not username:
        raise OSError("Cannot determine the current Windows user for file protection")

    try:
        result = subprocess.run(
            [
                "icacls",
                str(file_path),
                "/inheritance:r",
                "/grant:r",
                f"{username}:(F)",
            ],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError as error:
        raise OSError(f"Could not restrict access to {file_path}") from error

    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise OSError(f"Could not restrict access to {file_path}: {detail}")
