import os
import json
from datetime import datetime, timezone

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class AzureADSSO:
    def __init__(self, tenant_id=None, client_id=None, client_secret=None):
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = None
        self._id_token = None
        self._refresh_token = None
        self._token_expiry = None
        self._user_info = None
        self._roles = []

    def get_auth_url(self, redirect_uri="http://localhost", scope="openid profile email User.Read"):
        if not self._tenant_id or not self._client_id:
            return {"success": False, "error": "tenant_id and client_id required"}
        auth_url = (
            f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/authorize"
            f"?client_id={self._client_id}"
            f"&response_type=code"
            f"&redirect_uri={redirect_uri}"
            f"&scope={scope}"
            f"&response_mode=query"
            f"&state={os.urandom(16).hex()}"
        )
        return {"success": True, "auth_url": auth_url}

    def authenticate(self, auth_code=None, redirect_uri="http://localhost", username=None, password=None):
        if not REQUESTS_AVAILABLE:
            return {"success": False, "error": "requests library not installed"}

        if auth_code:
            return self._auth_code_flow(auth_code, redirect_uri)
        elif username and password:
            return self._resource_owner_flow(username, password)
        return {"success": False, "error": "Provide auth_code or username/password"}

    def _auth_code_flow(self, auth_code, redirect_uri):
        try:
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": redirect_uri,
                "client_id": self._client_id,
                "scope": "openid profile email User.Read",
            }
            if self._client_secret:
                data["client_secret"] = self._client_secret
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                return self._process_token_response(response.json())
            return {"success": False, "error": f"Token request failed: {response.status_code} - {response.text[:200]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _resource_owner_flow(self, username, password):
        try:
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": self._client_id,
                "scope": "openid profile email User.Read",
            }
            if self._client_secret:
                data["client_secret"] = self._client_secret
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                return self._process_token_response(response.json())
            return {"success": False, "error": f"Auth failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_token_response(self, token_data):
        self._access_token = token_data.get("access_token")
        self._id_token = token_data.get("id_token")
        self._refresh_token = token_data.get("refresh_token")
        self._token_expiry = datetime.now(timezone.utc).timestamp() + token_data.get("expires_in", 3600)
        if self._id_token:
            try:
                import base64
                parts = self._id_token.split(".")
                if len(parts) >= 2:
                    payload = parts[1]
                    padding = 4 - len(payload) % 4
                    if padding != 4:
                        payload += "=" * padding
                    decoded = base64.b64decode(payload).decode("utf-8")
                    claims = json.loads(decoded)
                    self._user_info = {
                        "sub": claims.get("sub"),
                        "name": claims.get("name"),
                        "email": claims.get("email") or claims.get("preferred_username"),
                        "oid": claims.get("oid"),
                        "tid": claims.get("tid"),
                    }
                    self._roles = claims.get("roles", [])
            except Exception:
                pass
        return {
            "success": True,
            "expires_in": token_data.get("expires_in"),
            "user": self._user_info,
        }

    def refresh_token(self):
        if not self._refresh_token:
            return {"success": False, "error": "No refresh token available"}
        try:
            token_url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "scope": "openid profile email User.Read",
            }
            if self._client_secret:
                data["client_secret"] = self._client_secret
            response = requests.post(token_url, data=data, timeout=30)
            if response.status_code == 200:
                return self._process_token_response(response.json())
            return {"success": False, "error": f"Refresh failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_info(self):
        if self._user_info:
            return {"success": True, "user": self._user_info}
        if not self._access_token:
            return {"success": False, "error": "Not authenticated"}
        try:
            url = "https://graph.microsoft.com/v1.0/me"
            headers = {"Authorization": f"Bearer {self._access_token}"}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                user = response.json()
                self._user_info = {
                    "display_name": user.get("displayName"),
                    "email": user.get("mail") or user.get("userPrincipalName"),
                    "job_title": user.get("jobTitle"),
                    "department": user.get("department"),
                    "office_location": user.get("officeLocation"),
                    "id": user.get("id"),
                }
                return {"success": True, "user": self._user_info}
            return {"success": False, "error": f"Failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_roles(self):
        return list(self._roles)

    def has_role(self, role):
        return role in self._roles

    def check_access(self, required_roles=None):
        if not self._access_token:
            return {"authorized": False, "reason": "Not authenticated"}
        if self._token_expiry and datetime.now(timezone.utc).timestamp() > self._token_expiry:
            return {"authorized": False, "reason": "Token expired"}
        if required_roles:
            has_all = all(role in self._roles for role in required_roles)
            if not has_all:
                missing = [r for r in required_roles if r not in self._roles]
                return {"authorized": False, "reason": f"Missing roles: {missing}", "missing_roles": missing}
        return {"authorized": True, "user": self._user_info}

    def logout(self):
        self._access_token = None
        self._id_token = None
        self._refresh_token = None
        self._token_expiry = None
        self._user_info = None
        self._roles = []
        return {"success": True}

    def get_session_info(self):
        return {
            "authenticated": bool(self._access_token),
            "user": self._user_info,
            "roles": self._roles,
            "token_expiry": self._token_expiry,
            "is_expired": self._token_expiry and datetime.now(timezone.utc).timestamp() > self._token_expiry,
        }
