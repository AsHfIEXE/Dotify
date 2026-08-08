from unittest.mock import patch

from dotify.api.api import SpotifyApi
from dotify.api.totp import Totp


def test_cookie_values_are_never_written_to_debug_log(tmp_path):
    secret = "sensitive-sp-dc-value"
    cookies = tmp_path / "cookies.txt"
    cookies.write_text(
        "# Netscape HTTP Cookie File\n"
        f".spotify.com\tTRUE\t/\tTRUE\t2147483647\tsp_dc\t{secret}\n",
        encoding="utf-8",
    )

    with patch("dotify.api.api.logger.debug") as debug:
        parsed = SpotifyApi._parse_cookies(str(cookies))

    assert parsed["sp_dc"] == secret
    logged = repr(debug.call_args_list)
    assert secret not in logged
    assert "sp_dc" in logged


def test_generated_totp_value_is_not_written_to_debug_log():
    totp = Totp(version="1", secret=b"secret")

    with patch("dotify.api.totp.logger.debug") as debug:
        code = totp.generate(1_700_000_000_000)

    logged = repr(debug.call_args_list)
    assert code not in logged
    assert "Generated TOTP code" in logged
