"""Google Drive integration with OAuth 2.0, full file management, and version history."""

import json
import io
import time
import hashlib
import logging
from typing import Any, Optional
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


class GoogleDriveIntegration:
    """Google Drive integration providing OAuth 2.0 auth, CRUD, search, permissions, and versioning."""

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    API_BASE = "https://www.googleapis.com/drive/v3"
    UPLOAD_BASE = "https://www.googleapis.com/upload/drive/v3"

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/callback"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.token_expiry: float = 0
        self._session = None

    def get_auth_url(self, state: str = "pdfmind") -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict:
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        data = await self._post_token(payload)
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expiry = time.time() + data.get("expires_in", 3600) - 300
        return data

    async def refresh_access_token(self) -> str:
        if not self.refresh_token:
            raise RuntimeError("No refresh token available. Re-authorize.")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        data = await self._post_token(payload)
        self.access_token = data["access_token"]
        self.token_expiry = time.time() + data.get("expires_in", 3600) - 300
        return self.access_token

    async def _ensure_token(self):
        if time.time() >= self.token_expiry:
            await self.refresh_access_token()

    async def _get_token(self, payload: dict) -> dict:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(self.TOKEN_URL, data=payload) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def _post_token(self, payload: dict) -> dict:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(self.TOKEN_URL, data=payload) as resp:
                resp.raise_for_status()
                return await resp.json()

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.access_token}"}

    async def list_files(self, folder_id: str = "root", page_size: int = 100, page_token: str = None,
                         query: str = None, fields: str = None) -> dict:
        await self._ensure_token()
        params: dict[str, Any] = {
            "q": f"'{folder_id}' in parents and trashed=false" if folder_id else "trashed=false",
            "pageSize": page_size,
            "fields": fields or "nextPageToken,files(id,name,mimeType,size,modifiedTime,version,owners)",
        }
        if query:
            params["q"] += f" and name contains '{query}'"
        if page_token:
            params["pageToken"] = page_token
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.API_BASE}/files", params=params, headers=self._headers()) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def search(self, query: str, page_size: int = 50) -> list[dict]:
        await self._ensure_token()
        full_query = f"trashed=false and name contains '{query}'"
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/files",
                params={"q": full_query, "pageSize": page_size, "fields": "files(id,name,mimeType,size,modifiedTime)"},
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("files", [])

    async def get_file_metadata(self, file_id: str) -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/files/{file_id}",
                params={"fields": "*"},
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def download_file(self, file_id: str) -> bytes:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/files/{file_id}", params={"alt": "media"}, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def upload_file(self, name: str, file_data: bytes, folder_id: str = "root",
                           mime_type: str = "application/pdf") -> dict:
        await self._ensure_token()
        metadata = {"name": name, "mimeType": mime_type}
        if folder_id:
            metadata["parents"] = [folder_id]
        import aiohttp
        form = aiohttp.FormData()
        form.add_field("metadata", json.dumps(metadata), content_type="application/json")
        form.add_field("file", file_data, filename=name, content_type=mime_type)
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.UPLOAD_BASE}/files?uploadType=multipart",
                data=form,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def update_file(self, file_id: str, file_data: bytes, mime_type: str = "application/pdf") -> dict:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{self.UPLOAD_BASE}/files/{file_id}?uploadType=media",
                data=file_data,
                headers={**self._headers(), "Content-Type": mime_type},
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def delete_file(self, file_id: str) -> bool:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(f"{self.API_BASE}/files/{file_id}", headers=self._headers()) as resp:
                return resp.status == 204

    async def create_folder(self, name: str, parent_id: str = "root") -> dict:
        metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/files", json=metadata, headers=self._headers()
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def set_permission(self, file_id: str, email: str, role: str = "reader",
                              notify: bool = True) -> dict:
        await self._ensure_token()
        perm = {"type": "user", "role": role, "emailAddress": email}
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.API_BASE}/files/{file_id}/permissions",
                params={"sendNotificationEmail": notify},
                json=perm,
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def remove_permission(self, file_id: str, permission_id: str) -> bool:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.API_BASE}/files/{file_id}/permissions/{permission_id}",
                headers=self._headers(),
            ) as resp:
                return resp.status == 204

    async def list_permissions(self, file_id: str) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/files/{file_id}/permissions",
                params={"fields": "permissions(id,emailAddress,role,type)"},
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("permissions", [])

    async def list_revisions(self, file_id: str) -> list[dict]:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/files/{file_id}/revisions",
                params={"fields": "revisions(id,modifiedTime,size,keepForever)"},
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("revisions", [])

    async def download_revision(self, file_id: str, revision_id: str) -> bytes:
        await self._ensure_token()
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.API_BASE}/files/{file_id}/revisions/{revision_id}",
                params={"alt": "media"},
                headers=self._headers(),
            ) as resp:
                resp.raise_for_status()
                return await resp.read()

    async def create_shared_link(self, file_id: str, role: str = "reader") -> dict:
        return await self.set_permission(file_id, email="", role=role, notify=False)

    def get_export_url(self, file_id: str, export_type: str = "application/pdf") -> str:
        return f"{self.API_BASE}/files/{file_id}/export?mimeType={export_type}"
