import os
import stat
import subprocess

from dotify.security import restrict_file_to_current_user


def test_sensitive_files_are_private_to_the_current_user(tmp_path):
    path = tmp_path / "credentials.json"
    path.write_text("{}", encoding="utf-8")

    restrict_file_to_current_user(path)

    if os.name != "nt":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        return

    result = subprocess.run(
        ["icacls", str(path)],
        capture_output=True,
        check=True,
        text=True,
    )
    acl = result.stdout.lower()
    assert os.environ["USERNAME"].lower() in acl
    assert "everyone:" not in acl
    assert "builtin\\users:" not in acl
    assert "(f)" in acl
