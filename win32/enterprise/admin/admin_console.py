import os
import json
import hashlib
import secrets
from datetime import datetime, timezone


class AdminConsole:
    def __init__(self, data_dir=None):
        self._data_dir = data_dir or os.path.join(os.path.expanduser("~"), ".pdf_editor", "admin")
        os.makedirs(self._data_dir, exist_ok=True)
        self._users = {}
        self._roles = {
            "admin": {"permissions": ["read", "write", "delete", "manage_users", "manage_settings", "view_audit", "export"]},
            "editor": {"permissions": ["read", "write", "export"]},
            "viewer": {"permissions": ["read"]},
            "auditor": {"permissions": ["read", "view_audit", "export"]},
        }
        self._audit_log = []
        self._usage_stats = {"documents_opened": 0, "documents_edited": 0, "documents_exported": 0, "sessions": 0}
        self._settings = {"max_upload_size_mb": 100, "allowed_formats": ["pdf"], "session_timeout_minutes": 30}
        self._load_data()

    def _load_data(self):
        users_file = os.path.join(self._data_dir, "users.json")
        audit_file = os.path.join(self._data_dir, "audit.json")
        settings_file = os.path.join(self._data_dir, "settings.json")
        try:
            if os.path.exists(users_file):
                with open(users_file, 'r') as f:
                    self._users = json.load(f)
        except Exception:
            pass
        try:
            if os.path.exists(audit_file):
                with open(audit_file, 'r') as f:
                    self._audit_log = json.load(f)
        except Exception:
            pass
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    saved_settings = json.load(f)
                    self._settings.update(saved_settings)
        except Exception:
            pass

    def _save_users(self):
        try:
            with open(os.path.join(self._data_dir, "users.json"), 'w') as f:
                json.dump(self._users, f, indent=2)
        except Exception:
            pass

    def _save_audit(self):
        try:
            with open(os.path.join(self._data_dir, "audit.json"), 'w') as f:
                json.dump(self._audit_log[-5000:], f, indent=2)
        except Exception:
            pass

    def _save_settings(self):
        try:
            with open(os.path.join(self._data_dir, "settings.json"), 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception:
            pass

    def create_user(self, username, password, role="viewer", display_name="", email=""):
        if username in self._users:
            return {"success": False, "error": "User already exists"}
        if role not in self._roles:
            return {"success": False, "error": f"Invalid role: {role}. Valid roles: {list(self._roles.keys())}"}
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        self._users[username] = {
            "password_hash": password_hash,
            "salt": salt,
            "role": role,
            "display_name": display_name or username,
            "email": email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None,
            "is_active": True,
            "login_attempts": 0,
        }
        self._save_users()
        self._log_audit("user_created", username, f"Role: {role}")
        return {"success": True, "username": username, "role": role}

    def authenticate(self, username, password):
        if username not in self._users:
            self._log_audit("login_failed", username, "User not found")
            return {"success": False, "error": "Invalid credentials"}
        user = self._users[username]
        if not user.get("is_active", True):
            return {"success": False, "error": "Account is disabled"}
        if user.get("login_attempts", 0) >= 5:
            return {"success": False, "error": "Account locked due to too many failed attempts"}
        salt = user["salt"]
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        if password_hash != user["password_hash"]:
            user["login_attempts"] = user.get("login_attempts", 0) + 1
            self._save_users()
            self._log_audit("login_failed", username, "Wrong password")
            return {"success": False, "error": "Invalid credentials"}
        user["last_login"] = datetime.now(timezone.utc).isoformat()
        user["login_attempts"] = 0
        self._save_users()
        self._usage_stats["sessions"] += 1
        self._log_audit("login_success", username, "")
        return {"success": True, "user": self._get_user_safe(username)}

    def _get_user_safe(self, username):
        user = self._users.get(username, {})
        return {k: v for k, v in user.items() if k not in ("password_hash", "salt")}

    def update_user(self, username, **kwargs):
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        user = self._users[username]
        allowed_fields = {"display_name", "email", "role", "is_active"}
        updated = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == "role" and value not in self._roles:
                    continue
                user[key] = value
                updated.append(key)
        if "password" in kwargs and kwargs["password"]:
            salt = secrets.token_hex(16)
            user["salt"] = salt
            user["password_hash"] = hashlib.sha256((salt + kwargs["password"]).encode()).hexdigest()
            updated.append("password")
        self._save_users()
        self._log_audit("user_updated", username, f"Fields: {', '.join(updated)}")
        return {"success": True, "updated_fields": updated}

    def delete_user(self, username):
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        del self._users[username]
        self._save_users()
        self._log_audit("user_deleted", username, "")
        return {"success": True}

    def list_users(self):
        return {uname: self._get_user_safe(uname) for uname in self._users}

    def check_permission(self, username, permission):
        if username not in self._users:
            return False
        role = self._users[username].get("role", "viewer")
        role_perms = self._roles.get(role, {}).get("permissions", [])
        return permission in role_perms

    def get_usage_stats(self):
        return {**self._usage_stats, "total_users": len(self._users), "active_users": len([u for u in self._users.values() if u.get("is_active", True)])}

    def record_usage(self, event_type):
        if event_type in self._usage_stats:
            self._usage_stats[event_type] += 1

    def _log_audit(self, action, user="", details=""):
        self._audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user": user,
            "details": details,
        })
        self._save_audit()

    def get_audit_log(self, limit=100, action_filter=None):
        log = self._audit_log
        if action_filter:
            log = [e for e in log if e["action"] == action_filter]
        return log[-limit:]

    def update_settings(self, **kwargs):
        for key, value in kwargs.items():
            if key in self._settings:
                self._settings[key] = value
        self._save_settings()
        self._log_audit("settings_updated", "", str(kwargs))
        return {"success": True, "settings": self._settings}

    def get_settings(self):
        return dict(self._settings)

    def get_roles(self):
        return {name: info["permissions"] for name, info in self._roles.items()}

    def change_password(self, username, old_password, new_password):
        if username not in self._users:
            return {"success": False, "error": "User not found"}
        user = self._users[username]
        salt = user["salt"]
        if hashlib.sha256((salt + old_password).encode()).hexdigest() != user["password_hash"]:
            return {"success": False, "error": "Current password is incorrect"}
        new_salt = secrets.token_hex(16)
        user["salt"] = new_salt
        user["password_hash"] = hashlib.sha256((new_salt + new_password).encode()).hexdigest()
        self._save_users()
        self._log_audit("password_changed", username, "")
        return {"success": True}
