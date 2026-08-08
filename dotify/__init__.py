from .version import PUBLIC_API_VERSION, __api_version__, __version__

__all__ = [
    "DotifyClient",
    "DotifySettings",
    "DownloadResult",
    "PluginManager",
    "PUBLIC_API_VERSION",
    "__api_version__",
    "__version__",
]


def __getattr__(name: str):
    if name in {"DotifyClient", "DotifySettings", "DownloadResult"}:
        from .client import DotifyClient, DotifySettings, DownloadResult

        return {
            "DotifyClient": DotifyClient,
            "DotifySettings": DotifySettings,
            "DownloadResult": DownloadResult,
        }[name]
    if name == "PluginManager":
        from .plugins import PluginManager

        return PluginManager
    raise AttributeError(name)
