from enum import Enum


class AudioDownloadMode(Enum):
    YTDLP = "ytdlp"
    ARIA2C = "aria2c"
    CURL = "curl"


class AudioRemuxMode(Enum):
    FFMPEG = "ffmpeg"
    MP4BOX = "mp4box"
    MP4DECRYPT = "mp4decrypt"


class VideoRemuxMode(Enum):
    FFMPEG = "ffmpeg"
    MP4BOX = "mp4box"
