from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from pyfreedom.core import Session


class Librespot:
    def __init__(
        self,
        credentials_path: str | Path,
    ) -> None:
        self.credentials_path = Path(credentials_path).expanduser()
        self.session = None

        self._initialize()

    def _configuration(self, *, store_credentials: bool):
        return (
            Session.Configuration.Builder()
            .set_store_credentials(store_credentials)
            .set_stored_credential_file(str(self.credentials_path))
            .set_cache_enabled(False)
            .build()
        )

    def _initialize(self) -> None:
        if not self.credentials_path.is_file():
            raise FileNotFoundError(self.credentials_path)

        builder = Session.Builder()
        builder.conf = self._configuration(store_credentials=False)
        builder.stored_file(str(self.credentials_path))
        if builder.login_credentials is None:
            raise ValueError(f"Invalid Librespot credentials file: {self.credentials_path}")

        self.session = builder.create()

    @classmethod
    def authorize(
        cls,
        credentials_path: str | Path,
        auth_url_callback: Callable[[str], None] | None = None,
    ) -> "Librespot":
        """Run Librespot OAuth and persist reusable credentials."""

        instance = cls.__new__(cls)
        instance.credentials_path = Path(credentials_path).expanduser()
        instance.session = None
        instance.credentials_path.parent.mkdir(parents=True, exist_ok=True)

        builder = Session.Builder()
        builder.conf = instance._configuration(store_credentials=True)
        builder.oauth(auth_url_callback)
        instance.session = builder.create()

        if not instance.credentials_path.is_file():
            instance.close()
            raise RuntimeError("Librespot did not create a credentials file")

        os.chmod(instance.credentials_path, 0o600)
        return instance

    def close(self) -> None:
        if self.session is not None:
            self.session.close()
            self.session = None
