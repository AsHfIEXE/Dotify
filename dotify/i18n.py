"""Small, dependency-free localization layer for user-facing Dotify text."""

from __future__ import annotations

import locale
import os
from dataclasses import dataclass
from typing import Any

SUPPORTED_LANGUAGES = ("en", "tr")

CATALOGS: dict[str, dict[str, str]] = {
    "en": {
        "starting": "Starting Dotify {version}",
        "processing_url": "Processing {url}",
        "fetch_error": "Error fetching media: {error}",
        "unknown_title": "Unknown Title",
        "would_download": 'Would download "{title}"',
        "downloading": 'Downloading "{title}"',
        "skipping": 'Skipping "{title}": {error}',
        "download_error": 'Error downloading "{title}"',
        "network_error": "Network error:",
        "authentication_error": "Authentication error:",
        "spotify_request_error": "Spotify request error:",
        "initialization_error": "Initialization error:",
        "network_timeout": "Spotify session initialization timed out. Authentication was not rejected.",
        "network_failed": "Spotify session initialization failed: {details}",
        "network_fix": "Check your connection and retry.",
        "cookies_refreshed": "Spotify web cookie refreshed from {browser}",
        "finished": "Finished: {success} successful, {skipped} skipped, {errors} failed in {duration}",
        "preflight_running": "Running preflight checks...",
        "preflight_failed": "Preflight checks failed:",
        "preflight_warnings": "Preflight warnings:",
        "preflight_passed": "[OK] Preflight checks passed",
        "fix": "Fix: {fix}",
        "queue_title": "Download queue",
        "select_media": "Select tracks to add to the download queue:",
        "playlist_action": "What would you like to do with this playlist?",
        "playlist_download_all": "Download all tracks",
        "playlist_choose_tracks": "Choose tracks",
        "playlist_streaming_all": "All playlist tracks will be downloaded in streaming order.",
        "queue_empty": "No media selected.",
        "summary_title": "Download summary",
        "summary_success": "Successful",
        "summary_skipped": "Skipped",
        "summary_failed": "Failed",
        "summary_duration": "Duration",
        "summary_bytes": "Transferred",
        "summary_formats": "Actual formats",
        "fallback_title": "Quality fallbacks",
        "fallback_media": "Media",
        "fallback_requested": "Requested",
        "fallback_actual": "Downloaded",
        "fallback_path": "File",
        "downloaded_format": "Downloaded as {actual}: {path}",
        "fallback_downloaded": "Quality fallback: {requested} -> {actual}. File: {path}",
        "status_waiting": "Waiting",
        "status_downloading": "Downloading",
        "status_rate_limited": "Waiting for Spotify (429)",
        "rate_limit_countdown": "retry in {seconds}s ({retry}/{total})",
        "status_success": "Complete",
        "status_skipped": "Skipped",
        "status_failed": "Failed",
        "init_title": "Dotify first-time setup",
        "init_language": "Choose a language:",
        "init_output": "Music output directory:",
        "init_quality": "Choose an audio quality profile:",
        "init_cookies": "Spotify cookies.txt path:",
        "init_wvd": "Widevine device.wvd path (optional):",
        "init_tui": "Enable the terminal interface by default?",
        "init_wait": "Wait time between downloads (seconds):",
        "init_exists": "Configuration already exists at {path}. Overwrite it?",
        "init_cancelled": "Setup cancelled; the existing configuration was kept.",
        "init_complete": "Configuration created at {path}",
        "init_next": "Next: run 'dotify env doctor', then download a Spotify URL.",
        "quality_balanced": "Balanced — Vorbis 320 kbps with fallback",
        "quality_compatible": "Compatible — AAC 128 kbps",
        "quality_lossless": "Lossless — FLAC with AAC fallback (Premium)",
    },
    "tr": {
        "starting": "Dotify {version} başlatılıyor",
        "processing_url": "İşleniyor: {url}",
        "fetch_error": "Medya alınamadı: {error}",
        "unknown_title": "Bilinmeyen Başlık",
        "would_download": 'İndirilecek: "{title}"',
        "downloading": 'İndiriliyor: "{title}"',
        "skipping": 'Atlanıyor: "{title}": {error}',
        "download_error": 'İndirme hatası: "{title}"',
        "network_error": "Ağ hatası:",
        "authentication_error": "Kimlik doğrulama hatası:",
        "spotify_request_error": "Spotify istek hatası:",
        "initialization_error": "Başlatma hatası:",
        "network_timeout": "Spotify oturumu zaman aşımına uğradı; kimlik bilgileri reddedilmedi.",
        "network_failed": "Spotify oturumu başlatılamadı: {details}",
        "network_fix": "Ağ bağlantınızı kontrol edip yeniden deneyin.",
        "cookies_refreshed": "Spotify web çerezi {browser} tarayıcısından yenilendi",
        "finished": "Tamamlandı: {success} başarılı, {skipped} atlandı, {errors} başarısız — {duration}",
        "preflight_running": "Ön kontroller çalıştırılıyor...",
        "preflight_failed": "Ön kontroller başarısız:",
        "preflight_warnings": "Ön kontrol uyarıları:",
        "preflight_passed": "[OK] Ön kontroller başarılı",
        "fix": "Çözüm: {fix}",
        "queue_title": "İndirme kuyruğu",
        "select_media": "İndirme kuyruğuna eklenecek parçaları seçin:",
        "playlist_action": "Bu playlist için ne yapmak istersiniz?",
        "playlist_download_all": "Tüm parçaları indir",
        "playlist_choose_tracks": "Parça seç",
        "playlist_streaming_all": "Playlistin tüm parçaları sırayla indirilecek.",
        "queue_empty": "Hiçbir medya seçilmedi.",
        "summary_title": "İndirme özeti",
        "summary_success": "Başarılı",
        "summary_skipped": "Atlandı",
        "summary_failed": "Başarısız",
        "summary_duration": "Süre",
        "summary_bytes": "Aktarılan",
        "summary_formats": "Gerçek biçimler",
        "fallback_title": "Kalite fallback'leri",
        "fallback_media": "Medya",
        "fallback_requested": "İstenen",
        "fallback_actual": "İndirilen",
        "fallback_path": "Dosya",
        "downloaded_format": "{actual} olarak indirildi: {path}",
        "fallback_downloaded": "Kalite fallback'i: {requested} -> {actual}. Dosya: {path}",
        "status_waiting": "Bekliyor",
        "status_downloading": "İndiriliyor",
        "status_rate_limited": "Spotify bekleniyor (429)",
        "rate_limit_countdown": "{seconds} sn sonra yeniden denenecek ({retry}/{total})",
        "status_success": "Tamamlandı",
        "status_skipped": "Atlandı",
        "status_failed": "Başarısız",
        "init_title": "Dotify ilk kurulum",
        "init_language": "Dil seçin:",
        "init_output": "Müzik çıktı klasörü:",
        "init_quality": "Ses kalitesi profili seçin:",
        "init_cookies": "Spotify cookies.txt yolu:",
        "init_wvd": "Widevine device.wvd yolu (isteğe bağlı):",
        "init_tui": "Terminal arayüzü varsayılan olarak açılsın mı?",
        "init_wait": "İndirmeler arasındaki bekleme süresi (saniye):",
        "init_exists": "{path} konumunda yapılandırma var. Üzerine yazılsın mı?",
        "init_cancelled": "Kurulum iptal edildi; mevcut yapılandırma korundu.",
        "init_complete": "Yapılandırma oluşturuldu: {path}",
        "init_next": "Sıradaki adım: 'dotify env doctor' çalıştırın ve bir Spotify URL'si indirin.",
        "quality_balanced": "Dengeli — fallback ile Vorbis 320 kbps",
        "quality_compatible": "Uyumlu — AAC 128 kbps",
        "quality_lossless": "Kayıpsız — AAC fallback ile FLAC (Premium)",
    },
}


def detect_language(requested: str | None = None) -> str:
    """Resolve an explicit, environment, or system language to a supported code."""

    candidate = requested
    if not candidate or candidate == "auto":
        candidate = os.environ.get("DOTIFY_LANGUAGE")
    if not candidate:
        candidate = locale.getlocale()[0] or "en"
    normalized = candidate.lower().replace("-", "_").split("_", 1)[0]
    return normalized if normalized in SUPPORTED_LANGUAGES else "en"


@dataclass(frozen=True, slots=True)
class Translator:
    language: str = "auto"

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", detect_language(self.language))

    def __call__(self, key: str, **values: Any) -> str:
        template = CATALOGS[self.language].get(key, CATALOGS["en"].get(key, key))
        return template.format(**values)
