import uuid
from dataclasses import dataclass, field

from ..interface.enums import AudioQuality
from ..interface.types import SpotifyMedia


@dataclass
class DownloadItem:
    media: SpotifyMedia
    uuid_: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    final_path: str | None = None
    staged_path: str | None = None
    playlist_file_path: str | None = None
    synced_lyrics_path: str | None = None
    cover_path: str | None = None
    candidate_final_paths: tuple[str, ...] = ()
    source_url: str | None = None

    @property
    def selected_audio_quality(self) -> str | None:
        stream_info = getattr(self.media, "stream_info", None)
        audio_track = getattr(stream_info, "audio_track", None)
        return getattr(audio_track, "audio_quality", None)

    @property
    def audio_description(self) -> str | None:
        quality = self.selected_audio_quality
        if not quality:
            return None
        try:
            return AudioQuality(quality).display_name
        except ValueError:
            return quality

    @property
    def fallback_audio_description(self) -> str | None:
        stream_info = getattr(self.media, "stream_info", None)
        audio_track = getattr(stream_info, "audio_track", None)
        qualities = getattr(audio_track, "fallback_from", None)
        if not qualities:
            return None
        descriptions = []
        for quality in qualities.split(","):
            try:
                descriptions.append(AudioQuality(quality).display_name)
            except ValueError:
                descriptions.append(quality)
        return ", ".join(descriptions)
