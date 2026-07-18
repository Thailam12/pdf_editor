"""WebDAV integration: connect to any WebDAV server with full file operations and locking."""

import logging
import xml.etree.ElementTree as ET
from typing import Any, Optional
from datetime import datetime
from urllib.parse import quote, unquote, urljoin

logger = logging.getLogger(__name__)

DAV_NAMESPACES = {
    "d": "DAV:",
    "oc": "http://owncloud.org/ns",
    "nc": "http://nextcloud.org/ns",
}


class WebDAVResource:
    """Represents a WebDAV resource (file or folder)."""

    def __init__(self, href: str, is_collection: bool = False, content_type: str = "",
                 content_length: int = 0, last_modified: str = "", etag: str = "",
                 created: str = ""):
        self.href = href
        self.is_collection = is_collection
        self.content_type = content_type
        self.content_length = content_length
        self.last_modified = last_modified
        self.etag = etag
        self.created = created

    @property
    def name(self) -> str:
        return unquote(self.href.rstrip("/").split("/")[-1])

    @property
    def is_pdf(self) -> bool:
        return self.name.lower().endswith(".pdf")

    def to_dict(self) -> dict:
        return {
            "href": self.href, "name": self.name,
            "is_collection": self.is_collection, "content_type": self.content_type,
            "content_length": self.content_length, "last_modified": self.last_modified,
            "etag": self.etag, "created": self.created, "is_pdf": self.is_pdf,
        }


class WebDAVIntegration:
    """WebDAV client supporting any compliant server with PROPFIND, upload, download, lock, and props."""

    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self._session = None

    @property
    def _auth(self) -> tuple[str, str]:
        return (self.username, self.password)

    def _url(self, path: str = "") -> str:
        return f"{self.base_url}/{path.lstrip('/')}" if path else self.base_url

    async def _request(self, method: str, url: str, data: bytes = None,
                       headers: dict = None) -> tuple[int, dict, bytes]:
        import aiohttp
        req_headers = headers or {}
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, auth=self._auth, data=data,
                headers=req_headers, allow_redirects=True,
            ) as resp:
                body = await resp.read()
                resp_headers = dict(resp.headers)
                return resp.status, resp_headers, body

    async def check_connection(self) -> bool:
        try:
            status, _, _ = await self._request("OPTIONS", self.base_url)
            return status < 400
        except Exception as e:
            logger.error(f"WebDAV connection check failed: {e}")
            return False

    async def propfind(self, path: str = "", depth: int = 1,
                       props: list[str] = None) -> list[WebDAVResource]:
        url = self._url(path)
        prop_names = props or [
            "getcontenttype", "getcontentlength", "getlastmodified",
            "getetag", "creationdate", "resourcetype",
        ]
        xml_parts = ["<?xml version='1.0' encoding='utf-8'?>",
                     "<d:propfind xmlns:d='DAV:'>"]
        for p in prop_names:
            xml_parts.append(f"<d:prop><d:{p}/></d:prop>")
        xml_parts.append("</d:propfind>")
        body = "".join(xml_parts).encode()
        status, headers, content = await self._request(
            "PROPFIND", url, data=body,
            headers={"Content-Type": "application/xml", "Depth": str(depth)},
        )
        if status not in (200, 207):
            raise RuntimeError(f"PROPFIND failed with status {status}")
        return self._parse_propfind_response(content)

    def _parse_propfind_response(self, xml_content: bytes) -> list[WebDAVResource]:
        resources = []
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return resources
        for response in root.iter(f"{{{DAV_NAMESPACES['d']}}}response"):
            href_el = response.find(f"{{{DAV_NAMESPACES['d']}}}href")
            if href_el is None or href_el.text is None:
                continue
            href = unquote(href_el.text)
            props_el = response.find(f"{{{DAV_NAMESPACES['d']}}}prop")
            is_collection = False
            content_type = ""
            content_length = 0
            last_modified = ""
            etag = ""
            created = ""
            if props_el is not None:
                rt = props_el.find(f"{{{DAV_NAMESPACES['d']}}}resourcetype")
                if rt is not None and rt.find(f"{{{DAV_NAMESPACES['d']}}}collection") is not None:
                    is_collection = True
                ct = props_el.find(f"{{{DAV_NAMESPACES['d']}}}getcontenttype")
                if ct is not None and ct.text:
                    content_type = ct.text
                cl = props_el.find(f"{{{DAV_NAMESPACES['d']}}}getcontentlength")
                if cl is not None and cl.text:
                    content_length = int(cl.text)
                lm = props_el.find(f"{{{DAV_NAMESPACES['d']}}}getlastmodified")
                if lm is not None and lm.text:
                    last_modified = lm.text
                et = props_el.find(f"{{{DAV_NAMESPACES['d']}}}getetag")
                if et is not None and et.text:
                    etag = et.text.strip('"')
                cd = props_el.find(f"{{{DAV_NAMESPACES['d']}}}creationdate")
                if cd is not None and cd.text:
                    created = cd.text
            resources.append(WebDAVResource(
                href=href, is_collection=is_collection, content_type=content_type,
                content_length=content_length, last_modified=last_modified,
                etag=etag, created=created,
            ))
        return resources

    async def list_directory(self, path: str = "") -> list[WebDAVResource]:
        return await self.propfind(path, depth=1)

    async def list_recursive(self, path: str = "") -> list[WebDAVResource]:
        return await self.propfind(path, depth="infinity")

    async def upload_file(self, remote_path: str, data: bytes,
                          content_type: str = "application/pdf") -> bool:
        url = self._url(remote_path)
        status, _, _ = await self._request(
            "PUT", url, data=data,
            headers={"Content-Type": content_type, "Content-Length": str(len(data))},
        )
        return status in (200, 201, 204)

    async def upload_chunked(self, remote_path: str, data: bytes, chunk_size: int = 10 * 1024 * 1024) -> bool:
        url = self._url(remote_path)
        total = len(data)
        offset = 0
        while offset < total:
            chunk = data[offset:offset + chunk_size]
            status, _, _ = await self._request("PUT", url, data=chunk, headers={
                "Content-Type": "application/pdf",
                "Content-Range": f"bytes {offset}-{offset + len(chunk) - 1}/{total}",
            })
            offset += chunk_size
            if status >= 400:
                return False
        return True

    async def download_file(self, remote_path: str) -> bytes:
        url = self._url(remote_path)
        status, _, body = await self._request("GET", url)
        if status != 200:
            raise RuntimeError(f"Download failed with status {status}")
        return body

    async def delete(self, remote_path: str) -> bool:
        url = self._url(remote_path)
        status, _, _ = await self._request("DELETE", url)
        return status in (200, 204)

    async def mkdir(self, remote_path: str) -> bool:
        url = self._url(remote_path)
        status, _, _ = await self._request("MKCOL", url)
        return status == 201

    async def move(self, source: str, destination: str) -> bool:
        status, _, _ = await self._request("MOVE", self._url(source), headers={
            "Destination": self._url(destination),
            "Overwrite": "T",
        })
        return status in (200, 201, 204)

    async def copy(self, source: str, destination: str) -> bool:
        status, _, _ = await self._request("COPY", self._url(source), headers={
            "Destination": self._url(destination),
            "Overwrite": "T",
        })
        return status in (200, 201, 204)

    async def lock(self, remote_path: str, timeout: int = 1800) -> Optional[str]:
        url = self._url(remote_path)
        lock_xml = (
            "<?xml version='1.0' encoding='utf-8'?>"
            "<d:lockinfo xmlns:d='DAV:'>"
            "<d:lockscope><d:exclusive/></d:lockscope>"
            "<d:locktype><d:write/></d:locktype>"
            "<d:owner><d:href>pdfmind</d:href></d:owner>"
            f"<d:timeout>Second-{timeout}</d:timeout>"
            "</d:lockinfo>"
        )
        status, headers, body = await self._request(
            "LOCK", url, data=lock_xml.encode(),
            headers={"Content-Type": "application/xml", "Timeout": f"Second-{timeout}"},
        )
        if status not in (200, 201):
            return None
        try:
            root = ET.fromstring(body)
            lock_token = root.find(".//{DAV:}locktoken/{DAV:}href")
            if lock_token is not None and lock_token.text:
                return lock_token.text.strip()
        except ET.ParseError:
            pass
        return headers.get("Lock-Token", "").strip("<>")

    async def unlock(self, remote_path: str, lock_token: str) -> bool:
        url = self._url(remote_path)
        status, _, _ = await self._request(
            "UNLOCK", url, headers={"Lock-Token": lock_token},
        )
        return status == 200

    async def refresh_lock(self, remote_path: str, lock_token: str, timeout: int = 1800) -> bool:
        url = self._url(remote_path)
        status, _, _ = await self._request(
            "LOCK", url,
            headers={"Lock-Token": lock_token, "Timeout": f"Second-{timeout}"},
        )
        return status == 200

    async def get_props(self, remote_path: str) -> dict:
        resources = await self.propfind(remote_path, depth=0)
        return resources[0].to_dict() if resources else {}

    async def set_prop(self, remote_path: str, namespace: str, name: str, value: str) -> bool:
        xml = (
            f"<?xml version='1.0' encoding='utf-8'?>"
            f"<d:proppatch xmlns:d='DAV:' xmlns:custom='{namespace}'>"
            f"<d:set><d:prop><custom:{name}>{value}</custom:{name}></d:prop></d:set>"
            f"</d:proppatch>"
        )
        status, _, _ = await self._request(
            "PROPPATCH", self._url(remote_path),
            data=xml.encode(), headers={"Content-Type": "application/xml"},
        )
        return status in (200, 204, 207)

    async def search_files(self, query: str, path: str = "") -> list[WebDAVResource]:
        resources = await self.list_directory(path)
        query_lower = query.lower()
        return [r for r in resources if query_lower in r.name.lower()]

    async def get_quota(self) -> dict:
        resources = await self.propfind("", depth=0)
        if resources:
            props = resources[0]
            return {"used": 0, "available": 0, "href": props.href}
        return {"used": 0, "available": 0}
