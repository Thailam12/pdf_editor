import os
import json
from datetime import datetime, timezone

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class OneDriveIntegration:
    def __init__(self, client_id=None, tenant_id=None):
        self._client_id = client_id
        self._tenant_id = tenant_id or "common"
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None
        self._base_url = "https://graph.microsoft.com/v1.0"

    def authenticate(self, client_id=None, tenant_id=None, auth_code=None, redirect_uri="http://localhost"):
        self._client_id = client_id or self._client_id
        self._tenant_id = tenant_id or self._tenant_id

        if not self._client_id:
            return {"success": False, "error": "client_id is required"}

        if not REQUESTS_AVAILABLE:
            return {"success": False, "error": "requests library not installed"}

        if auth_code:
            return self._exchange_code(auth_code, redirect_uri)
        else:
            auth_url = (f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/authorize"
                        f"?client_id={self._client_id}"
                        f"&response_type=code"
                        f"&redirect_uri={redirect_uri}"
                        f"&scope=Files.ReadWrite.All%20User.Read"
                        f"&response_mode=query")
            return {"success": True, "auth_url": auth_url, "message": "Open URL in browser to authenticate"}

    def _exchange_code(self, auth_code, redirect_uri):
        try:
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": self._client_id,
                "scope": "Files.ReadWrite.All User.Read",
            }
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token")
                self._token_expiry = datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 3600)
                return {"success": True, "expires_in": token_data.get("expires_in")}
            return {"success": False, "error": f"Token exchange failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _refresh_access_token(self):
        if not self._refresh_token:
            return False
        try:
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "scope": "Files.ReadWrite.All User.Read",
            }
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get("access_token")
                self._refresh_token = token_data.get("refresh_token", self._refresh_token)
                self._token_expiry = datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 3600)
                return True
        except Exception:
            pass
        return False

    def _get_headers(self):
        if not self._access_token:
            raise RuntimeError("Not authenticated")
        if self._token_expiry and datetime.now(timezone.utc).timestamp() > self._token_expiry:
            self._refresh_access_token()
        return {"Authorization": f"Bearer {self._access_token}", "Content-Type": "application/json"}

    def list_files(self, folder_path="drive/root", top=50):
        try:
            url = f"{self._base_url}/{folder_path}/children"
            params = {"$top": top, "$orderby": "lastModifiedDateTime desc",
                      "$select": "name,size,lastModifiedDateTime,createdDateTime,file,folder,webUrl,id"}
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            if response.status_code == 200:
                files = []
                for item in response.json().get("value", []):
                    if item.get("file"):
                        files.append({
                            "id": item.get("id"),
                            "name": item.get("name"),
                            "size": item.get("size", 0),
                            "modified": item.get("lastModifiedDateTime"),
                            "created": item.get("createdDateTime"),
                            "url": item.get("webUrl"),
                            "is_pdf": item.get("name", "").lower().endswith(".pdf"),
                        })
                return {"success": True, "files": files, "count": len(files)}
            return {"success": False, "error": f"List failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_shared(self):
        try:
            url = f"{self._base_url}/me/drive/shared"
            params = {"$top": 50}
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=30)
            if response.status_code == 200:
                files = []
                for item in response.json().get("value", []):
                    files.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "size": item.get("size", 0),
                        "modified": item.get("lastModifiedDateTime"),
                        "url": item.get("webUrl"),
                    })
                return {"success": True, "files": files, "count": len(files)}
            return {"success": False, "error": f"Failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def download_file(self, file_id, local_path):
        try:
            url = f"{self._base_url}/me/drive/items/{file_id}/content"
            response = requests.get(url, headers=self._get_headers(), timeout=60, stream=True)
            if response.status_code == 200:
                os.makedirs(os.path.dirname(local_path) or '.', exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return {"success": True, "local_path": local_path, "size": os.path.getsize(local_path)}
            return {"success": False, "error": f"Download failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_file(self, local_path, folder_path="drive/root:"):
        if not os.path.exists(local_path):
            return {"success": False, "error": f"File not found: {local_path}"}
        try:
            file_name = os.path.basename(local_path)
            upload_url = f"{self._base_url}/{folder_path}/{file_name}:/content"
            with open(local_path, 'rb') as f:
                file_data = f.read()
            headers = self._get_headers()
            headers["Content-Type"] = "application/pdf"
            response = requests.put(upload_url, headers=headers, data=file_data, timeout=120)
            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "success": True,
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "url": result.get("webUrl"),
                    "size": result.get("size", 0),
                }
            return {"success": False, "error": f"Upload failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_sync_status(self, file_id):
        try:
            url = f"{self._base_url}/me/drive/items/{file_id}"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            if response.status_code == 200:
                item = response.json()
                return {
                    "success": True,
                    "name": item.get("name"),
                    "size": item.get("size"),
                    "last_modified": item.get("lastModifiedDateTime"),
                    "parent_reference": item.get("parentReference", {}).get("path", ""),
                }
            return {"success": False, "error": f"Failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_info(self):
        try:
            url = f"{self._base_url}/me"
            response = requests.get(url, headers=self._get_headers(), timeout=30)
            if response.status_code == 200:
                user = response.json()
                return {
                    "success": True,
                    "display_name": user.get("displayName"),
                    "email": user.get("mail") or user.get("userPrincipalName"),
                    "id": user.get("id"),
                }
            return {"success": False, "error": f"Failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_file(self, file_id):
        try:
            url = f"{self._base_url}/me/drive/items/{file_id}"
            response = requests.delete(url, headers=self._get_headers(), timeout=30)
            return {"success": response.status_code in (200, 204)}
        except Exception as e:
            return {"success": False, "error": str(e)}
