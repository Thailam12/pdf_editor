"""Box integration with OAuth 2.0, enterprise content management, and collaboration."""

import json
import time
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

API_BASE = "https://api.box.com/2.0"
UPLOAD_BASE = "https://upload.box.com/api/2.0"


class BoxIntegration:
    """Box enterprise content management: OAuth 2.0, files, folders, collaborations, and metadata."""

    AUTH_URL = "https://account.box.com/api/oauth2/authorize"
    TOKEN_URL = "https://api.box.com/oauth2/token"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/box/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: float = 0
        self.enterprise_id: Optional[str] = None

    def get_auth_url(self, state: str = "pdfmind") -> str:
        from urllib.parse import urlencode
        params = {
            "client_id": self.client_id,
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
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self._apply_token(data)
                return data

    async def refresh_access_token(self) -> str:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                self._apply_token(data)
                return self.access_token

    def _apply_token(self, data: dict):
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expiry = time.time() + data.get("expires_in", 3600) - 300

    async def _ensure_token(self):
        if time.time() >= self.token_expiry:
            await self.refresh_access_token()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def get_user(self, user_id: str = "me") -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/users/{user_id}", headers=self._headers()) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def list_folder(self, folder_id: str = "0", offset: int = 0, limit: int = 100,
                          fields: str = None) -> dict:
        await self._ensure_token()
        params: dict[str, Any] = {"offset": offset, "limit": limit}
        if fields:
            params["fields"] = fields
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/folders/{folder_id}/items", params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_folder(self, folder_id: str = "0", fields: str = None) -> dict:
        await self._ensure_token()
        params = {}
        if fields:
            params["fields"] = fields
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/folders/{folder_id}", params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def create_folder(self, name: str, parent_id: str = "0") -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/folders",
                json={"name": name, "parent": {"id": parent_id}},
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def delete_folder(self, folder_id: str, recursive: bool = True) -> bool:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{API_BASE}/folders/{folder_id}",
                params={"recursive": str(recursive).lower()},
                headers=self._headers(),
            ) as resp:
                return resp.status in (200, 204)

    async def upload_file(self, file_name: str, file_data: bytes, parent_id: str = "0",
                          content_type: str = "application/pdf") -> dict:
        await self._ensure_token()
        import aiohttp
        form = aiohttp.FormData()
        attributes = {"name": file_name, "parent": {"id": parent_id}}
        form.add_field("attributes", json.dumps(attributes), content_type="application/json")
        form.add_field("file", file_data, filename=file_name, content_type=content_type)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{UPLOAD_BASE}/files/content", data=form, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                entries = data.get("entries", [])
                return entries[0] if entries else {}

    async def upload_large_file(self, file_name: str, file_data: bytes, parent_id: str = "0") -> dict:
        await self._ensure_token()
        import aiohttp
        chunk_size = 10 * 1024 * 1024
        total_size = len(file_data)
        async with aiohttp.ClientSession() as session:
            upload_session = await session.post(
                f"{UPLOAD_BASE}/files/upload_session/start",
                data=file_data[:chunk_size],
                headers={**self._headers(), "Content-Type": "application/octet-stream",
                          "X-BoxApi-Extra": json.dumps({"total_size": total_size})},
            )
            session_id = (await upload_session.json())["session_id"]
            offset = chunk_size
            while offset < total_size:
                chunk = file_data[offset:offset + chunk_size]
                is_last = (offset + chunk_size >= total_size)
                await session.post(
                    f"{UPLOAD_BASE}/files/upload_session/{'commit' if is_last else 'append'}",
                    data=chunk,
                    headers={**self._headers(), "Content-Type": "application/octet-stream",
                              "X-BoxApi-Extra": json.dumps({"part": {"offset": offset, "part_size": len(chunk)}}),
                              "X-Box-Upload-Session-Id": session_id},
                )
                offset += chunk_size
            return {"session_id": session_id}

    async def download_file(self, file_id: str) -> bytes:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/files/{file_id}/content", headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def get_file_info(self, file_id: str, fields: str = None) -> dict:
        await self._ensure_token()
        params = {}
        if fields:
            params["fields"] = fields
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/files/{file_id}", params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def delete_file(self, file_id: str) -> bool:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{API_BASE}/files/{file_id}", headers=self._headers()) as resp:
                return resp.status in (200, 204)

    async def create_collaboration(self, file_id: str, email: str, role: str = "viewer",
                                    item_type: str = "file") -> dict:
        await self._ensure_token()
        import aiohttp
        payload = {
            "item": {"id": file_id, "type": item_type},
            "accessible_by": {"login": email},
            "role": role,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/collaborations", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def list_collaborations(self, file_id: str, item_type: str = "file") -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/{item_type}s/{file_id}/collaborations", headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("entries", [])

    async def remove_collaboration(self, collab_id: str) -> bool:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{API_BASE}/collaborations/{collab_id}", headers=self._headers()
            ) as resp:
                return resp.status in (200, 204)

    async def search(self, query: str, limit: int = 20, file_extensions: list[str] = None) -> list[dict]:
        await self._ensure_token()
        params: dict[str, Any] = {"query": query, "limit": limit}
        if file_extensions:
            params["file_extensions"] = ",".join(file_extensions)
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/search", params=params, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("entries", [])

    async def get_versions(self, file_id: str) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/files/{file_id}/versions", headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("entries", [])

    async def promote_version(self, file_id: str, version_id: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/{file_id}/versions/{version_id}/promote",
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_comments(self, file_id: str) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/files/{file_id}/comments", headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("entries", [])

    async def add_comment(self, file_id: str, message: str) -> dict:
        await self._ensure_token()
        import aiohttp
        payload = {
            "item": {"id": file_id, "type": "file"},
            "message": message,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/comments", json=payload, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_metadata(self, file_id: str, scope: str = "global") -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/files/{file_id}/metadata/global/properties",
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def set_metadata(self, file_id: str, metadata: dict, scope: str = "global") -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/files/{file_id}/metadata/global/properties",
                json=metadata,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
