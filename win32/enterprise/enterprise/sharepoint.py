import os
import json
from datetime import datetime, timezone

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class SharePointIntegration:
    def __init__(self, tenant_id=None, client_id=None, client_secret=None, site_url=None):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._site_url = site_url
        self._access_token = None
        self._token_expiry = None

    def authenticate(self, tenant_id=None, client_id=None, client_secret=None):
        self._tenant_id = tenant_id or self._tenant_id
        self._client_id = client_id or self._client_id
        self._client_secret = client_secret or self._client_secret

        if not all([self._tenant_id, self._client_id, self._client_secret]):
            return {"success": False, "error": "Missing tenant_id, client_id, or client_secret"}

        if not REQUESTS_AVAILABLE:
            return {"success": False, "error": "requests library not installed"}

        try:
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "scope": "https://graph.microsoft.com/.default",
            }
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                self._token_expiry = datetime.now(timezone.utc).timestamp() + expires_in
                return {"success": True, "expires_in": expires_in}
            else:
                return {"success": False, "error": f"Auth failed: {response.status_code} - {response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_headers(self):
        if not self._access_token:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

    def _check_token(self):
        if self._token_expiry and datetime.now(timezone.utc).timestamp() > self._token_expiry:
            self._access_token = None
            return False
        return bool(self._access_token)

    def list_documents(self, folder_path="/", top=50):
        if not self._check_token():
            return {"success": False, "error": "Token expired or not authenticated"}
        if not self._site_url:
            return {"success": False, "error": "Site URL not configured"}

        try:
            api_url = f"{self._site_url}/_api/web/GetFolderByServerRelativeUrl('{folder_path}')/Files"
            params = {"$top": top, "$orderby": "TimeLastModified desc"}
            response = requests.get(api_url, headers=self._get_headers(), params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                files = []
                for item in data.get("value", []):
                    if item.get("Name", "").lower().endswith(".pdf"):
                        files.append({
                            "name": item.get("Name"),
                            "server_relative_url": item.get("ServerRelativeUrl"),
                            "size": item.get("Length", 0),
                            "modified": item.get("TimeLastModified"),
                            "created": item.get("TimeCreated"),
                            "author": item.get("Author", {}).get("Title", ""),
                        })
                return {"success": True, "documents": files, "count": len(files)}
            else:
                return {"success": False, "error": f"API error: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_document(self, server_relative_url, local_path):
        if not self._check_token():
            return {"success": False, "error": "Not authenticated"}
        try:
            api_url = f"{self._site_url}/_api/web/GetFileByServerRelativeUrl('{server_relative_url}')/$value"
            response = requests.get(api_url, headers=self._get_headers(), timeout=60, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return {"success": True, "local_path": local_path, "size": os.path.getsize(local_path)}
            else:
                return {"success": False, "error": f"Download failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_document(self, local_path, folder_path="/"):
        if not self._check_token():
            return {"success": False, "error": "Not authenticated"}
        if not os.path.exists(local_path):
            return {"success": False, "error": f"File not found: {local_path}"}

        try:
            file_name = os.path.basename(local_path)
            api_url = f"{self._site_url}/_api/web/GetFolderByServerRelativeUrl('{folder_path}')/Files/add(url='{file_name}',overwrite=true)"
            with open(local_path, 'rb') as f:
                file_data = f.read()
            headers = self._get_headers()
            headers["Content-Type"] = "application/octet-stream"
            response = requests.post(api_url, headers=headers, data=file_data, timeout=120)
            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "success": True,
                    "server_relative_url": result.get("ServerRelativeUrl"),
                    "name": result.get("Name"),
                    "size": result.get("Length", 0),
                }
            else:
                return {"success": False, "error": f"Upload failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_out(self, server_relative_url):
        if not self._check_token():
            return {"success": False, "error": "Not authenticated"}
        try:
            api_url = f"{self._site_url}/_api/web/GetFileByServerRelativeUrl('{server_relative_url}')/CheckOut()"
            response = requests.post(api_url, headers=self._get_headers(), timeout=30)
            if response.status_code in (200, 204):
                return {"success": True, "status": "checked_out"}
            return {"success": False, "error": f"Check-out failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_in(self, server_relative_url, comment=""):
        if not self._check_token():
            return {"success": False, "error": "Not authenticated"}
        try:
            api_url = (f"{self._site_url}/_api/web/GetFileByServerRelativeUrl('{server_relative_url}')"
                       f"/CheckIn(comment='{comment}',checkintype=0)")
            response = requests.post(api_url, headers=self._get_headers(), timeout=30)
            if response.status_code in (200, 204):
                return {"success": True, "status": "checked_in"}
            return {"success": False, "error": f"Check-in failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_version_history(self, server_relative_url):
        if not self._check_token():
            return {"success": False, "error": "Not authenticated"}
        try:
            api_url = f"{self._site_url}/_api/web/GetFileByServerRelativeUrl('{server_relative_url}')/Versions"
            response = requests.get(api_url, headers=self._get_headers(), timeout=30)
            if response.status_code == 200:
                versions = []
                for v in response.json().get("value", []):
                    versions.append({
                        "version_id": v.get("ID"),
                        "created": v.get("Created"),
                        "created_by": v.get("CreatedBy", {}).get("Title", ""),
                        "size": v.get("Size", 0),
                        "url": v.get("Url", ""),
                    })
                return {"success": True, "versions": versions, "count": len(versions)}
            return {"success": False, "error": f"Failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_documents(self, query, top=20):
        if not self._check_token():
            return {"success": False, "error": "Not authenticated"}
        try:
            api_url = f"{self._site_url}/_api/web/sitepaths"
            search_url = f"https://graph.microsoft.com/v1.0/sites"
            headers = self._get_headers()
            params = {"search": query, "$top": top}
            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                results = []
                for item in response.json().get("value", []):
                    results.append({
                        "name": item.get("displayName"),
                        "url": item.get("webUrl"),
                        "id": item.get("id"),
                    })
                return {"success": True, "results": results}
            return {"success": False, "error": f"Search failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
