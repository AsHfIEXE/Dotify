from dotify.downloader.audio import SpotifyAudioDownloader
from dotify.downloader.video import SpotifyVideoDownloader


def test_ytdlp_progress_hook_is_forwarded_to_reporter(monkeypatch, tmp_path):
    events = []
    downloader = object.__new__(SpotifyAudioDownloader)
    downloader.silent = True
    downloader.progress_callback = events.append

    class FakeYdl:
        def __init__(self, params):
            self.params = params

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeHttpDownloader:
        def __init__(self, ydl, params):
            self.params = params
            self.hooks = []

        def add_progress_hook(self, hook):
            self.hooks.append(hook)

        def download(self, output_path, info):
            payload = {
                "status": "downloading",
                "downloaded_bytes": 64,
                "total_bytes": 128,
                "filename": output_path,
            }
            for hook in self.hooks:
                hook(payload)

    monkeypatch.setattr("dotify.downloader.audio.YoutubeDL", FakeYdl)
    monkeypatch.setattr("dotify.downloader.audio.HttpFD", FakeHttpDownloader)

    downloader._download_with_ytdlp("https://example.invalid/audio", tmp_path / "a.ogg")

    assert events[0]["downloaded_bytes"] == 64
    assert events[0]["total_bytes"] == 128


def test_fragment_progress_hook_is_forwarded_to_reporter(monkeypatch, tmp_path):
    events = []
    downloader = object.__new__(SpotifyVideoDownloader)
    downloader.silent = True
    downloader.progress_callback = events.append

    class FakeYdl:
        def __init__(self, params):
            self.params = params

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    class FakeFragmentDownloader:
        def __init__(self, ydl, params):
            self.hooks = []

        def add_progress_hook(self, hook):
            self.hooks.append(hook)

        def _prepare_and_start_frag_download(self, context, info):
            return None

        def download_and_append_fragments(self, context, segments, info):
            for hook in self.hooks:
                hook(
                    {
                        "status": "downloading",
                        "downloaded_bytes": 1,
                        "total_bytes": len(segments),
                    }
                )

        def _finish_multiline_status(self):
            return None

    monkeypatch.setattr("dotify.downloader.video.YoutubeDL", FakeYdl)
    monkeypatch.setattr(
        "dotify.downloader.video.FragmentFD", FakeFragmentDownloader
    )

    downloader._download_stream(tmp_path / "video.bin", ["one", "two"])

    assert events[0]["downloaded_bytes"] == 1
    assert events[0]["total_bytes"] == 2
