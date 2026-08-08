import asyncio
import datetime
import logging
import time
from collections.abc import Awaitable, Callable
from email.utils import parsedate_to_datetime
from http.cookiejar import MozillaCookieJar
from pathlib import Path

import base62
import httpx
from httpx_retries import RetryTransport, Retry

from ..utils import safe_json
from .constants import (
    AUDIO_STREAM_URLS_API_URL,
    CLIENT_TOKEN_URL,
    CLIENT_VERSION,
    COOKIE_DOMAIN,
    DEVICE_CLIENT_TOKEN,
    EXTENDED_METADATA_API_URL,
    GID_METADATA_URL,
    HOME_PAGE_URL,
    LYRICS_API_URL,
    PATHFINDER_API_URL,
    PLAYBACK_INFO_API_URL,
    PLAYPLAY_LICENSE_API_URL,
    SEEK_TABLE_API_URL,
    SERVER_TIME_URL,
    TIMEOUT,
    SESSION_TOKEN_URL,
    TRACK_CREDITS_API_URL,
    VIDEO_MANIFEST_API_URL,
    WIDEVINE_LICENSE_API_URL,
    WIDEVINE_MAX_AUTOMATIC_WAIT_SECONDS,
    WIDEVINE_MAX_RETRIES,
    WIDEVINE_RETRY_BACKOFF_SECONDS,
)
from .device_flow import SpotifyDeviceFlow
from .enums import SessionType
from .exceptions import (
    DotifyAuthenticationException,
    DotifyLibrespotAuthenticationException,
    DotifyLibrespotConnectionException,
    DotifyRequestException,
)
from .proto.extendedmetadata_pb2 import BatchedEntityRequest, BatchedExtensionResponse
from .proto.playplay_pb2 import PlayPlayLicenseRequest, PlayPlayLicenseResponse
from .totp import Totp

logger = logging.getLogger(__name__)


def _parse_retry_after(value: str | None) -> float | None:
    """Return a Retry-After delay in seconds for delta or HTTP-date values."""

    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=datetime.timezone.utc)
    return max(
        0.0,
        (retry_at - datetime.datetime.now(datetime.timezone.utc)).total_seconds(),
    )


class SpotifyApi:
    def __init__(
        self,
        sp_dc: str | None = None,
        session_type: SessionType = SessionType.LIBRESPOT,
        librespot_credentials_path: str | None = None,
        widevine_retries: int = WIDEVINE_MAX_RETRIES,
        widevine_backoff: int = WIDEVINE_RETRY_BACKOFF_SECONDS,
        widevine_max_wait: int = WIDEVINE_MAX_AUTOMATIC_WAIT_SECONDS,
        widevine_request_interval: float = 0,
        widevine_wait_callback: Callable[
            [float, int, int], Awaitable[None]
        ]
        | None = None,
    ) -> None:
        self.sp_dc = sp_dc
        self.session_type = session_type
        self.librespot_credentials_path = librespot_credentials_path or str(
            Path.home() / ".dotify" / "librespot_credentials.json"
        )
        self.widevine_retries = max(0, widevine_retries)
        self.widevine_backoff = max(1, widevine_backoff)
        self.widevine_max_wait = max(0, widevine_max_wait)
        self.widevine_request_interval = max(0.0, widevine_request_interval)
        self.widevine_wait_callback = widevine_wait_callback
        self._widevine_request_lock = asyncio.Lock()
        self._last_widevine_request_at = 0.0
        self.librespot = None

    @property
    def premium_session(self) -> bool:
        return (
            getattr(self, "user_profile", {})
            .get("data", {})
            .get("me", {})
            .get("account", {})
            .get("product")
            == "PREMIUM"
        )

    @property
    def anonymous_session(self) -> bool:
        return self.user_profile is None

    @staticmethod
    def _parse_cookies(cookies_path: str) -> dict[str, str]:
        cookies = MozillaCookieJar(cookies_path)
        cookies.load(ignore_discard=True, ignore_expires=True)

        cookie_dict = {
            cookie.name: cookie.value
            for cookie in cookies
            if cookie.domain == COOKIE_DOMAIN
        }

        logger.debug("Parsed Spotify cookie names: %s", sorted(cookie_dict))

        return cookie_dict

    @classmethod
    async def create_from_netscape_cookies(
        cls,
        cookies_path: str = "./cookies.txt",
        *args,
        **kwargs,
    ) -> "SpotifyApi":
        cookies = cls._parse_cookies(cookies_path)
        sp_dc = cookies.get("sp_dc")
        if sp_dc is None:
            raise DotifyAuthenticationException(
                "'sp_dc' cookie not found in cookies. "
                "Make sure you have exported the cookies "
                "from the Spotify homepage and are logged in."
            )

        return await cls.create(
            *args,
            sp_dc=sp_dc,
            **kwargs,
        )

    @classmethod
    async def create(
        cls,
        *args,
        **kwargs,
    ) -> "SpotifyApi":
        api = cls(*args, **kwargs)
        try:
            await api._initialize()
        except Exception:
            await api.aclose()
            raise

        return api

    async def _initialize(self) -> None:
        self._initialize_client()
        await self._initialize_authorization()
        await self._initialize_user_profile()
        if (
            self.session_type == SessionType.LIBRESPOT
            and not getattr(self, "is_anonymous_token", False)
        ):
            await asyncio.to_thread(self._initialize_librespot)

    def _initialize_client(self) -> None:
        self._transport = RetryTransport(
            retry=Retry(
                total=6,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
        )
        self.client = httpx.AsyncClient(
            transport=self._transport,
            timeout=TIMEOUT,
        )

        self.client.headers.update(
            {
                "accept": "application/json",
                "accept-language": "en-US",
                "content-type": "application/json",
                "origin": HOME_PAGE_URL,
                "priority": "u=1, i",
                "referer": HOME_PAGE_URL,
                "sec-ch-ua": '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "spotify-app-version": CLIENT_VERSION,
                "app-platform": "WebPlayer",
            }
        )

        if self.sp_dc:
            self.client.cookies.update({"sp_dc": self.sp_dc})

    async def _initialize_authorization(self) -> None:
        if self.session_type == SessionType.DESKTOP:
            await self._initialize_authorization_with_device_flow()
        elif self.session_type in {SessionType.LIBRESPOT, SessionType.WEB}:
            await self._initialize_authorization_with_totp()

    def _set_authorization_header(
        self,
        access_token: str,
        client_token: str | None = None,
    ) -> None:
        self.client.headers.update({"authorization": f"Bearer {access_token}"})
        if client_token:
            self.client.headers.update(
                {
                    "client-token": client_token,
                }
            )

    async def _initialize_authorization_with_totp(self) -> None:
        self.totp = await Totp.initialize()
        session_info = await self._get_session_token()
        self.is_anonymous_token = session_info.get("isAnonymous", False)
        client_token = await self._get_client_token(session_info["clientId"])

        access_token = session_info["accessToken"]
        granted_token = client_token["granted_token"]["token"]

        self._authorization_expire_time = (
            session_info["accessTokenExpirationTimestampMs"] / 1000
        )

        self._access_token = access_token
        self._client_token = granted_token

        self._set_authorization_header(access_token, granted_token)

    async def _initialize_authorization_with_device_flow(self) -> None:
        device_flow = SpotifyDeviceFlow(self.sp_dc)
        token_data = await device_flow.get_token()

        self._access_token = token_data["access_token"]

        self._set_authorization_header(
            token_data["access_token"],
            DEVICE_CLIENT_TOKEN,
        )
        self._authorization_expire_time = int(time.time()) + token_data["expires_in"]

    async def _initialize_user_profile(self) -> None:
        self.user_profile = await self._get_user_profile() if self.sp_dc else None

    def _initialize_librespot(self) -> None:
        from .librespot import Librespot

        try:
            self.librespot = Librespot(
                credentials_path=self.librespot_credentials_path,
            )
        except FileNotFoundError as error:
            raise DotifyLibrespotAuthenticationException(
                "Librespot credentials were not found at "
                f"{self.librespot_credentials_path}. Spotify cookies and "
                "Librespot OAuth credentials are separate."
            ) from error
        except ValueError as error:
            raise DotifyLibrespotAuthenticationException(
                "The stored Librespot credentials are invalid or unreadable."
            ) from error
        except (ConnectionError, TimeoutError, OSError) as error:
            details = str(error).strip() or type(error).__name__
            raise DotifyLibrespotConnectionException(
                f"Librespot could not connect to a Spotify access point: {details}"
            ) from error
        except Exception as error:
            if "403" in str(error):
                account = "Premium" if self.premium_session else "non-Premium"
                message = (
                    f"Spotify reports a {account} account, but rejected the stored "
                    "Librespot credentials while requesting its internal token "
                    "(status 403)."
                )
            else:
                message = f"Librespot session initialization failed: {error}"
            raise DotifyLibrespotAuthenticationException(message) from error

    async def aclose(self) -> None:
        librespot = getattr(self, "librespot", None)
        if librespot is not None:
            await asyncio.to_thread(librespot.close)
            self.librespot = None

        client = getattr(self, "client", None)
        if client is not None and not client.is_closed:
            await client.aclose()

    async def _get_server_time(self) -> int:
        response = await self.client.get(SERVER_TIME_URL)
        server_time = safe_json(response)
        if response.status_code != 200 or not server_time:
            raise DotifyRequestException(
                name="Server time",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received server time: {server_time}")

        return 1e3 * server_time["serverTime"]

    async def _get_session_token(self) -> dict:
        server_time = await self._get_server_time()

        generated_totp = self.totp.generate(timestamp=server_time)

        response = await self.client.get(
            SESSION_TOKEN_URL,
            params={
                "reason": "init",
                "productType": "web-player",
                "totp": generated_totp,
                "totpServer": generated_totp,
                "totpVer": self.totp.version,
            },
        )
        session_info = safe_json(response)
        if response.status_code != 200 or not session_info:
            raise DotifyRequestException(
                name="Session info",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug("Received Spotify session information")

        return session_info

    async def _get_client_token(self, client_id: str) -> None:
        response = await self.client.post(
            CLIENT_TOKEN_URL,
            json={
                "client_data": {
                    "client_version": CLIENT_VERSION,
                    "client_id": client_id,
                    "js_sdk_data": {},
                }
            },
            headers={
                "Accept": "application/json",
            },
        )
        client_token = safe_json(response)
        if response.status_code != 200 or not client_token:
            raise DotifyRequestException(
                name="Client token",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug("Received Spotify client token")

        return client_token

    async def _refresh_authorization_if_needed(self) -> None:
        timestamp_session_expire = int(self._authorization_expire_time)
        timestamp_now = time.time()
        if timestamp_now < timestamp_session_expire:
            return

        await self._initialize_authorization()

    @staticmethod
    def media_id_to_gid(media_id: str) -> str:
        return hex(base62.decode(media_id, base62.CHARSET_INVERTED))[2:].zfill(32)

    @staticmethod
    def gid_to_media_id(gid: str) -> str:
        return base62.encode(int(gid, 16), charset=base62.CHARSET_INVERTED).zfill(22)

    async def _pathfinder_request(
        self,
        operation_name: str,
        persisted_query_hash: str,
        variables: dict | None = None,
    ) -> dict:
        await self._refresh_authorization_if_needed()
        variables = variables or {}

        response = await self.client.post(
            PATHFINDER_API_URL,
            json={
                "variables": variables,
                "operationName": operation_name,
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": persisted_query_hash,
                    }
                },
            },
        )
        response_json = safe_json(response)

        if (
            response.status_code != 200
            or not response_json
            or "errors" in response_json
        ):
            raise DotifyRequestException(
                name="Pathfinder",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        return response_json

    async def _get_user_profile(self) -> dict:
        user_profile = await self._pathfinder_request(
            operation_name="accountAttributes",
            persisted_query_hash="24aaa3057b69fa91492de26841ad199bd0b330ca95817b7a4d6715150de01827",
        )

        logger.debug(f"Received user profile: {user_profile}")

        return user_profile

    async def get_track(self, track_id: str) -> dict:
        result = await self._pathfinder_request(
            operation_name="getTrack",
            persisted_query_hash="612585ae06ba435ad26369870deaae23b5c8800a256cd8a57e08eddc25a37294",
            variables={"uri": f"spotify:track:{track_id}"},
        )

        logger.debug(f"Received track: {result}")

        return result

    async def get_album(
        self,
        album_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        album = await self._pathfinder_request(
            operation_name="getAlbum",
            persisted_query_hash="b9bfabef66ed756e5e13f68a942deb60bd4125ec1f1be8cc42769dc0259b4b10",
            variables={
                "uri": f"spotify:album:{album_id}",
                "offset": offset,
                "limit": limit,
            },
        )

        logger.debug(f"Received album: {album}")

        return album

    async def get_playlist(
        self,
        playlist_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        playlist = await self._pathfinder_request(
            operation_name="fetchPlaylist",
            persisted_query_hash="bb67e0af06e8d6f52b531f97468ee4acd44cd0f82b988e15c2ea47b1148efc77",
            variables={
                "uri": f"spotify:playlist:{playlist_id}",
                "offset": offset,
                "limit": limit,
                "enableWatchFeedEntrypoint": True,
            },
        )

        logger.debug(f"Received playlist: {playlist}")

        return playlist

    async def get_episode(self, episode_id: str) -> dict:
        episode = await self._pathfinder_request(
            operation_name="getEpisodeOrChapter",
            persisted_query_hash="8a62dbdeb7bd79605d7d68b01bcdf83f08bc6c6287ee1665ba012c748a4cf1f3",
            variables={"uri": f"spotify:episode:{episode_id}"},
        )

        logger.debug(f"Received episode: {episode}")

        return episode

    async def get_show(
        self,
        show_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        show = await self._pathfinder_request(
            operation_name="queryPodcastEpisodes",
            persisted_query_hash="8e2826c5993383566cc08bf9f5d3301b69513c3f6acb8d706286855e57bf44b2",
            variables={
                "uri": f"spotify:show:{show_id}",
                "offset": offset,
                "limit": limit,
            },
        )

        logger.debug(f"Received show: {show}")

        return show

    async def get_artist_overview(self, artist_id: str) -> dict:
        artist_overview = await self._pathfinder_request(
            operation_name="queryArtistOverview",
            persisted_query_hash="5b9e64f43843fa3a9b6a98543600299b0a2cbbbccfdcdcef2402eb9c1017ca4c",
            variables={
                "uri": f"spotify:artist:{artist_id}",
                "preReleaseV2": False,
            },
        )

        logger.debug(f"Received artist overview: {artist_overview}")

        return artist_overview

    async def _get_artist_discography(
        self,
        artist_id: str,
        type: str,
        offeset: int,
        limit: int,
    ) -> dict:
        result = await self._pathfinder_request(
            operation_name=f"queryArtistDiscography{type.capitalize()}s",
            persisted_query_hash="5e07d323febb57b4a56a42abbf781490e58764aa45feb6e3dc0591564fc56599",
            variables={
                "uri": f"spotify:artist:{artist_id}",
                "offset": offeset,
                "limit": limit,
                "order": "DATE_DESC",
            },
        )

        logger.debug(f"Received artist {type}s: {result}")

        return result

    async def get_artist_albums(
        self,
        artist_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        return await self._get_artist_discography(
            artist_id=artist_id,
            type="album",
            offeset=offset,
            limit=limit,
        )

    async def get_artist_singles(
        self,
        artist_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        return await self._get_artist_discography(
            artist_id=artist_id,
            type="single",
            offeset=offset,
            limit=limit,
        )

    async def get_artist_compilations(
        self,
        artist_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        return await self._get_artist_discography(
            artist_id=artist_id,
            type="compilation",
            offeset=offset,
            limit=limit,
        )

    async def get_artist_videos(
        self,
        artist_id: str,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        artist_videos = await self._pathfinder_request(
            operation_name="queryArtistRelatedVideos",
            persisted_query_hash="8958042d3dd127ec7882a7117fafa4df21af27ff1560af51e55061e8451de67b",
            variables={
                "uri": f"spotify:artist:{artist_id}",
                "showMapped": True,
                "showUnmapped": True,
                "offset": offset,
                "limit": limit,
            },
        )

        logger.debug(f"Received artist videos: {artist_videos}")

        return artist_videos

    async def get_library_tracks(
        self,
        offset: int = 0,
        limit: int = 300,
    ) -> dict:
        library_tracks = await self._pathfinder_request(
            operation_name="fetchLibraryTracks",
            persisted_query_hash="087278b20b743578a6262c2b0b4bcd20d879c503cc359a2285baf083ef944240",
            variables={
                "offset": offset,
                "limit": limit,
            },
        )

        logger.debug(f"Received library tracks: {library_tracks}")

        return library_tracks

    async def get_video_manifest(
        self,
        file_id: str,
    ) -> dict:
        await self._refresh_authorization_if_needed()

        response = await self.client.get(VIDEO_MANIFEST_API_URL.format(file_id=file_id))
        video_manifest = safe_json(response)

        if response.status_code != 200 or not video_manifest:
            raise DotifyRequestException(
                name="Video manifest",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received video manifest: {video_manifest}")

        return video_manifest

    async def get_seek_table(self, file_id: str) -> dict:
        async with httpx.AsyncClient(
            transport=self._transport,
            timeout=TIMEOUT,
        ) as client:
            response = await client.get(
                SEEK_TABLE_API_URL.format(file_id=file_id),
                headers={
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "en-US",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Origin": HOME_PAGE_URL,
                    "Pragma": "no-cache",
                    "Priority": "u=4",
                    "Referer": HOME_PAGE_URL,
                    "Sec-Fetch-Dest": "empty",
                    "Sec-Fetch-Mode": "cors",
                    "Sec-Fetch-Site": "cross-site",
                    "User-Agent": self.client.headers["user-agent"],
                },
            )
        seek_table = safe_json(response)

        if response.status_code != 200 or not seek_table:
            raise DotifyRequestException(
                name="Seek table",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received seek table: {seek_table}")

        return seek_table

    async def get_playback_info(
        self,
        media_id: str,
        media_type: str,
        file_formats: list[str] | None = None,
    ) -> dict:
        await self._refresh_authorization_if_needed()
        file_formats = file_formats or ["file_ids_mp4", "manifest_ids_video"]

        response = await self.client.get(
            PLAYBACK_INFO_API_URL.format(
                media_id=media_id,
                media_type=media_type,
            ),
            params={
                "manifestFileFormat": file_formats,
            },
        )
        playback_info = safe_json(response)

        if response.status_code != 200 or not playback_info:
            raise DotifyRequestException(
                name="Playback info",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received track playback info: {playback_info}")

        return playback_info

    async def get_gid_metadata(
        self,
        media_id: str,
        media_type: str,
    ) -> dict:
        return await self._get_gid_metadata(
            gid=self.media_id_to_gid(media_id),
            media_type=media_type,
        )

    async def _get_gid_metadata(
        self,
        gid: str,
        media_type: str,
    ) -> dict:
        await self._refresh_authorization_if_needed()

        response = await self.client.get(
            GID_METADATA_URL.format(
                gid=gid,
                media_type=media_type,
            )
        )
        gid_metadata = safe_json(response)

        if response.status_code != 200 or not gid_metadata:
            raise DotifyRequestException(
                name="GID metadata",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received GID metadata: {gid_metadata}")

        return gid_metadata

    async def get_lyrics(self, track_id: str) -> dict:
        await self._refresh_authorization_if_needed()

        response = await self.client.get(LYRICS_API_URL.format(track_id=track_id))
        lyrics = safe_json(response)

        if response.status_code != 200 or not lyrics:
            raise DotifyRequestException(
                name="Lyrics",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received lyrics: {lyrics}")

        return lyrics

    async def get_track_credits(self, track_id: str) -> dict:
        await self._refresh_authorization_if_needed()

        response = await self.client.get(
            TRACK_CREDITS_API_URL.format(track_id=track_id)
        )
        track_credits = safe_json(response)

        if response.status_code != 200 or not track_credits:
            raise DotifyRequestException(
                name="Track credits",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received track credits: {track_credits}")

        return track_credits

    async def get_widevine_license(self, challenge: bytes, media_type: str) -> bytes:
        await self._refresh_authorization_if_needed()

        async with self._widevine_request_lock:
            retry_after = None
            for retry_index in range(self.widevine_retries + 1):
                elapsed = time.monotonic() - self._last_widevine_request_at
                pacing_delay = self.widevine_request_interval - elapsed
                if pacing_delay > 0:
                    logger.info(
                        "Pacing Widevine license requests; waiting %.1f seconds.",
                        pacing_delay,
                    )
                    await asyncio.sleep(pacing_delay)

                response = await self.client.post(
                    WIDEVINE_LICENSE_API_URL.format(type=media_type),
                    content=challenge,
                )
                self._last_widevine_request_at = time.monotonic()
                if response.status_code != 429:
                    break

                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                if retry_index >= self.widevine_retries:
                    break

                delay = retry_after
                if delay is None:
                    delay = self.widevine_backoff * (2**retry_index)
                if delay > self.widevine_max_wait:
                    logger.warning(
                        "Spotify rate-limited the Widevine license request and "
                        "requested a %.0f-second cooldown; automatic retry stopped.",
                        delay,
                    )
                    break

                logger.warning(
                    "Spotify rate-limited the Widevine license request (429); "
                    "retrying in %.0f seconds (%d/%d). Do not start another "
                    "Dotify process.",
                    delay,
                    retry_index + 1,
                    self.widevine_retries,
                )
                if self.widevine_wait_callback:
                    await self.widevine_wait_callback(
                        delay,
                        retry_index + 1,
                        self.widevine_retries,
                    )
                else:
                    await asyncio.sleep(delay)

        widevine_license = response.content

        if response.status_code != 200 or not widevine_license:
            raise DotifyRequestException(
                name="Widevine license",
                response_status_code=response.status_code,
                response_text=response.text,
                retry_after=retry_after,
            )

        logger.debug("Received Widevine license (%d bytes)", len(widevine_license))

        return widevine_license

    async def get_audio_stream_urls(self, format_id: str, file_id: str) -> dict:
        await self._refresh_authorization_if_needed()

        response = await self.client.get(
            AUDIO_STREAM_URLS_API_URL.format(format_id=format_id, file_id=file_id)
        )
        audio_stream_urls = safe_json(response)

        if response.status_code != 200 or not audio_stream_urls:
            raise DotifyRequestException(
                name="Audio stream URLs",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        logger.debug(f"Received audio stream URLs: {audio_stream_urls}")

        return audio_stream_urls

    async def get_playplay_license(
        self,
        file_id: str,
        request: PlayPlayLicenseRequest,
    ) -> PlayPlayLicenseResponse:
        await self._refresh_authorization_if_needed()

        response = await self.client.post(
            PLAYPLAY_LICENSE_API_URL.format(file_id=file_id),
            content=request.SerializeToString(),
            headers={
                "Accept": "application/x-protobuf",
                "Content-Type": "application/x-protobuf",
            },
        )
        response_bytes = response.content

        if response.status_code != 200 or not response_bytes:
            raise DotifyRequestException(
                name="PlayPlay license",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        playplay_license = PlayPlayLicenseResponse()
        playplay_license.ParseFromString(response_bytes)

        logger.debug("Received PlayPlay license")

        return playplay_license

    async def get_extended_metadata(
        self,
        request: BatchedEntityRequest,
    ) -> BatchedExtensionResponse:
        await self._refresh_authorization_if_needed()

        response = await self.client.post(
            EXTENDED_METADATA_API_URL,
            content=request.SerializeToString(),
            headers={
                "Accept": "application/x-protobuf",
                "Content-Type": "application/x-protobuf",
            },
        )
        response_bytes = response.content

        if response.status_code != 200 or not response_bytes:
            raise DotifyRequestException(
                name="Extended metadata",
                response_status_code=response.status_code,
                response_text=response.text,
            )

        extended_metadata = BatchedExtensionResponse()
        extended_metadata.ParseFromString(response_bytes)

        logger.debug(f"Received extended metadata: {extended_metadata}")

        return extended_metadata
