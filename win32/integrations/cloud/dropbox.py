"""Dropbox integration with OAuth 2.0, browsing, upload/download, shared links, and sync."""

import json
import time
import hashlib
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

API_BASE = "https://api.dropboxapi.com/2"
CONTENT_BASE = "https://content.dropboxapi.com/2"


class DropboxIntegration:
    """Full Dropbox integration: auth, file operations, sharing, and sync tracking."""

    AUTH_URL = "https://www.dropbox.com/oauth2/authorize"
    TOKEN_URL = "https://api.dropbox.com/oauth2/token"

    def __init__(self, app_key: str, app_secret: str, redirect_uri: str = "http://localhost:8080/dropbox/callback"):
        self.app_key = app_key
        self.app_secret = app_secret
        self.redirect_uri = redirect_uri
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.account_id: Optional[str] = None
        self.token_expiry: float = 0
        self._cursor: Optional[str] = None

    def get_auth_url(self, state: str = "pdfmind") -> str:
        from urllib.parse import urlencode
        params = {
            "client_id": self.app_key,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "grant_type": "authorization_code",
                    "client_id": self.app_key,
                    "client_secret": self.app_secret,
                    "redirect_uri": self.redirect_uri,
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self.access_token = data["access_token"]
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                self.account_id = data.get("account_id")
                self.token_expiry = time.time() + data.get("expires_in", 14400) - 300
                return data

    async def refresh_access_token(self) -> str:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.app_key,
                    "client_secret": self.app_secret,
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self.access_token = data["access_token"]
                self.token_expiry = time.time() + data.get("expires_in", 14400) - 300
                return self.access_token

    async def _ensure_token(self):
        if time.time() >= self.token_expiry:
            await self.refresh_access_token()

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def list_folder(self, path: str = "", recursive: bool = False) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/list_folder",
                json={"path": path, "recursive": recursive, "include_deleted": False},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def list_folder_continue(self) -> dict:
        if not self._cursor:
            return {"entries": [], "has_more": False}
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/list_folder/continue",
                json={"cursor": self._cursor},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_file_metadata(self, path: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/get_metadata",
                json={"path": path, "include_media_info": True},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def download_file(self, path: str) -> bytes:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CONTENT_BASE}/files/download",
                json={"path": path},
                headers={**self._auth_headers(), "Dropbox-API-Arg": json.dumps({"path": path})},
            ) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def upload_file(self, path: str, data: bytes, mode: str = "add",
                          autorename: bool = False, mute: bool = False) -> dict:
        await self._ensure_token()
        import aiohttp
        api_arg = {"path": path, "mode": mode, "autorename": autorename, "mute": mute}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CONTENT_BASE}/files/upload",
                data=data,
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/octet-stream",
                    "Dropbox-API-Arg": json.dumps(api_arg),
                },
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def upload_session_start(self, data: bytes) -> str:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{CONTENT_BASE}/files/upload_session/start",
                data=data,
                headers={
                    **self._auth_headers(),
                    "Content-Type": "application/octet-stream",
                    "Dropbox-API-Arg": json.dumps({"close": False}),
                },
            ) as resp:
                resp.raise_for_status()
                result = await resp.json()
                return result["session_id"]

    async def delete_file(self, path: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/delete_v2",
                json={"path": path},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def move_file(self, from_path: str, to_path: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/move_v2",
                json={"from_path": from_path, "to_path": to_path},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def copy_file(self, from_path: str, to_path: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/copy_v2",
                json={"from_path": from_path, "to_path": to_path},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def search(self, query: str, path: str = "", max_results: int = 100) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/search_v2",
                json={"query": query, "options": {"path": path, "max_results": max_results}},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("matches", [])

    async def create_shared_link(self, path: str, requested_visibility: str = "public") -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/sharing/create_shared_link_with_settings",
                json={"path": path, "settings": {"requested_visibility": requested_visibility}},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def list_shared_links(self, path: str = "", direct_only: bool = True) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/sharing/list_shared_links",
                json={"path": path, "direct_only": direct_only},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("links", [])

    async def revoke_shared_link(self, url: str) -> bool:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/sharing/revoke_shared_link",
                json={"url": url},
                headers=self._auth_headers(),
            ) as resp:
                return resp.status == 200

    async def list_revisions(self, path: str, limit: int = 10) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/list_revisions",
                json={"path": path, "limit": limit},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("entries", [])

    async def restore_revision(self, rev: str, path: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/restore",
                json={"rev": rev, "path": path},
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_space_usage(self) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/users/get_space_usage",
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_current_account(self) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/users/get_current_account",
                headers=self._auth_headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
