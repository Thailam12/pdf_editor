import os
import hashlib
import secrets
from datetime import datetime, timezone

import pymupdf


PERMISSION_FLAGS = {
    "print":          1 << 3,
    "modify":         1 << 4,
    "copy":           1 << 5,
    "annotate":       1 << 6,
    "fill_forms":     1 << 9,
    "extract":        1 << 10,
    "assemble":       1 << 11,
    "high_print":     1 << 12,
}


class PDFEncryptionService:
    def __init__(self):
        self._last_operation = None

    def encrypt_password(self, input_path, output_path, user_password="", owner_password=None,
                         permissions=None, algorithm="aes-256"):
        if owner_password is None:
            owner_password = user_password or secrets.token_hex(16)

        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        perm_flags = 0
        if permissions:
            for perm_name, perm_val in PERMISSION_FLAGS.items():
                if permissions.get(perm_name, True):
                    perm_flags |= perm_val
        else:
            perm_flags = 0
            for perm_val in PERMISSION_FLAGS.values():
                perm_flags |= perm_val

        enc_dict = self._get_encryption_dict(algorithm, user_password, owner_password, perm_flags)
        try:
            doc.save(output_path, encryption=enc_dict)
            doc.close()
        except TypeError:
            try:
                doc.save(output_path, garbage=4, deflate=True, owner_pw=owner_password,
                         user_pw=user_password, encryption=pymupdf.PDF_ENCRYPT_AES_256)
                doc.close()
            except Exception as e:
                doc.close()
                return {"success": False, "error": str(e)}
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        self._last_operation = {
            "action": "encrypt",
            "input": input_path,
            "output": output_path,
            "algorithm": algorithm,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {
            "success": True,
            "output_path": output_path,
            "algorithm": algorithm,
            "permissions": permissions or {k: True for k in PERMISSION_FLAGS},
            "has_user_password": bool(user_password),
            "has_owner_password": bool(owner_password),
        }

    def _get_encryption_dict(self, algorithm, user_pw, owner_pw, perm_flags):
        algo_map = {
            "rc4-40": pymupdf.PDF_ENCRYPT_RC4_40,
            "rc4-128": pymupdf.PDF_ENCRYPT_RC4_128,
            "aes-128": pymupdf.PDF_ENCRYPT_AES_128,
            "aes-256": pymupdf.PDF_ENCRYPT_AES_256,
        }
        enc_type = algo_map.get(algorithm, pymupdf.PDF_ENCRYPT_AES_256)
        return {
            "owner_password": owner_pw,
            "user_password": user_pw,
            "encryption": enc_type,
            "permissions": perm_flags,
        }

    def decrypt(self, input_path, output_path, password):
        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        if doc.needs_pass():
            authenticated = doc.authenticate(password)
            if not authenticated:
                doc.close()
                return {"success": False, "error": "Authentication failed - wrong password"}

        try:
            doc.save(output_path, garbage=4, deflate=True, linear=True)
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        self._last_operation = {
            "action": "decrypt",
            "input": input_path,
            "output": output_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {"success": True, "output_path": output_path}

    def set_permissions(self, input_path, output_path, password, permissions):
        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        if doc.needs_pass():
            auth = doc.authenticate(password)
            if not auth:
                doc.close()
                return {"success": False, "error": "Authentication failed"}

        perm_flags = 0
        for perm_name, enabled in permissions.items():
            flag = PERMISSION_FLAGS.get(perm_name)
            if flag and enabled:
                perm_flags |= flag

        try:
            doc.save(output_path, garbage=4, deflate=True, encryption=pymupdf.PDF_ENCRYPT_AES_256,
                     owner_pw=password, user_pw="", permissions=perm_flags)
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        return {"success": True, "output_path": output_path, "permissions": permissions}

    def get_encryption_info(self, path):
        try:
            doc = pymupdf.open(path)
            encrypted = doc.needs_pass()
            permissions = doc.get_permissions() if encrypted else 0
            doc.close()

            active_permissions = {}
            for name, flag in PERMISSION_FLAGS.items():
                active_permissions[name] = bool(permissions & flag)

            return {
                "encrypted": encrypted,
                "permissions_raw": permissions,
                "permissions": active_permissions,
                "can_print": active_permissions.get("print", False),
                "can_modify": active_permissions.get("modify", False),
                "can_copy": active_permissions.get("copy", False),
                "can_annotate": active_permissions.get("annotate", False),
            }
        except Exception as e:
            return {"error": str(e)}

    def apply_time_limited_access(self, input_path, output_path, password, expiry_hours=24):
        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        expiry_info = {
            "expires_at": datetime.now(timezone.utc).isoformat(),
            "expiry_hours": expiry_hours,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        meta = doc.metadata or {}
        meta["Subject"] = f"TIME_LIMITED|{expiry_info['expires_at']}|{expiry_hours}h"
        doc.set_metadata(meta)

        try:
            doc.save(output_path, garbage=4, deflate=True,
                     encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw=password, user_pw="")
            doc.close()
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "output_path": output_path,
            "expires_at": expiry_info["expires_at"],
            "expiry_hours": expiry_hours,
        }

    def check_access_validity(self, path):
        try:
            doc = pymupdf.open(path)
            meta = doc.metadata or {}
            doc.close()
            subject = meta.get("Subject", "")
            if subject.startswith("TIME_LIMITED|"):
                parts = subject.split("|")
                if len(parts) >= 3:
                    expires_str = parts[1]
                    hours = int(parts[2].replace("h", ""))
                    expires_at = datetime.fromisoformat(expires_str)
                    now = datetime.now(timezone.utc)
                    if now > expires_at:
                        return {"valid": False, "expired": True, "expired_at": expires_str, "message": "Access has expired"}
                    remaining = (expires_at - now).total_seconds() / 3600
                    return {"valid": True, "expired": False, "hours_remaining": round(remaining, 1)}
            return {"valid": True, "expired": False, "message": "No time limit set"}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_supported_algorithms(self):
        return [
            {"id": "rc4-40", "name": "RC4 40-bit", "strength": "weak", "deprecated": True},
            {"id": "rc4-128", "name": "RC4 128-bit", "strength": "moderate", "deprecated": True},
            {"id": "aes-128", "name": "AES 128-bit", "strength": "strong", "deprecated": False},
            {"id": "aes-256", "name": "AES 256-bit", "strength": "very_strong", "deprecated": False},
        ]

    def get_last_operation(self):
        return self._last_operation
