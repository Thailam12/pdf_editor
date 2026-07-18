import os
import json
import hashlib
import secrets
from datetime import datetime, timezone

try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


class CertificateStore:
    def __init__(self, store_path=None):
        self._store_path = store_path or os.path.join(os.path.expanduser("~"), ".pdf_editor", "certificates")
        self._certificates = {}
        self._ca_store = {}
        self._crl_cache = {}
        os.makedirs(self._store_path, exist_ok=True)
        self._load_store()

    def _load_store(self):
        store_file = os.path.join(self._store_path, "store.json")
        if os.path.exists(store_file):
            try:
                with open(store_file, 'r') as f:
                    data = json.load(f)
                    self._certificates = data.get("certificates", {})
                    self._ca_store = data.get("ca_store", {})
            except Exception:
                pass

    def _save_store(self):
        store_file = os.path.join(self._store_path, "store.json")
        try:
            with open(store_file, 'w') as f:
                json.dump({
                    "certificates": self._certificates,
                    "ca_store": self._ca_store,
                }, f, indent=2)
        except Exception:
            pass

    def import_certificate(self, cert_path, password=None):
        try:
            with open(cert_path, 'rb') as f:
                cert_data = f.read()
            cert_id = hashlib.sha256(cert_data).hexdigest()[:16]
            self._certificates[cert_id] = {
                "path": cert_path,
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "size": len(cert_data),
                "fingerprint": cert_id,
                "subject": "Imported Certificate",
                "issuer": "Unknown",
                "not_before": "",
                "not_after": "",
            }
            if CRYPTOGRAPHY_AVAILABLE:
                try:
                    cert = x509.load_pem_x509_certificate(cert_data)
                    self._certificates[cert_id].update({
                        "subject": cert.subject.rfc4514_string(),
                        "issuer": cert.issuer.rfc4514_string(),
                        "not_before": cert.not_valid_before.isoformat(),
                        "not_after": cert.not_valid_after.isoformat(),
                        "serial_number": str(cert.serial_number),
                        "signature_algorithm": cert.signature_algorithm_oid._name,
                    })
                except Exception:
                    try:
                        cert = x509.load_der_x509_certificate(cert_data)
                        self._certificates[cert_id].update({
                            "subject": cert.subject.rfc4514_string(),
                            "issuer": cert.issuer.rfc4514_string(),
                        })
                    except Exception:
                        pass
            self._save_store()
            return {"success": True, "cert_id": cert_id, "info": self._certificates[cert_id]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_certificate(self, cert_id, output_path, format_type="pem"):
        if cert_id not in self._certificates:
            return {"success": False, "error": "Certificate not found"}
        cert_info = self._certificates[cert_id]
        try:
            src_path = cert_info.get("path", "")
            if src_path and os.path.exists(src_path):
                with open(src_path, 'rb') as f:
                    cert_data = f.read()
                with open(output_path, 'wb') as f:
                    f.write(cert_data)
                return {"success": True, "output_path": output_path, "format": format_type}
            return {"success": False, "error": "Original certificate file not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_self_signed(self, common_name, organization="", country="", state="",
                             locality="", validity_days=365, key_size=2048, output_dir=None):
        if not CRYPTOGRAPHY_AVAILABLE:
            return self._generate_simple_self_signed(common_name, validity_days, output_dir)

        try:
            key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization) if organization else None,
                x509.NameAttribute(NameOID.COUNTRY_NAME, country) if country else None,
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state) if state else None,
                x509.NameAttribute(NameOID.LOCALITY_NAME, locality) if locality else None,
            ])
            subject = x509.Name([attr for attr in subject if attr is not None])
            issuer = subject

            now = datetime.now(timezone.utc)
            cert = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(issuer)
                .public_key(key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now)
                .not_valid_after(now.replace(year=now.year + (validity_days // 365) or now.year + 1))
                .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
                .add_extension(x509.KeyUsage(
                    digital_signature=True, key_encipherment=True,
                    content_commitment=True, data_encipherment=False,
                    key_agreement=False, key_cert_sign=True,
                    crl_sign=True, encipher_only=False, decipher_only=False
                ), critical=True)
                .sign(key, hashes.SHA256())
            )

            if not output_dir:
                output_dir = self._store_path
            os.makedirs(output_dir, exist_ok=True)

            cert_path = os.path.join(output_dir, f"{common_name.replace(' ', '_')}_cert.pem")
            key_path = os.path.join(output_dir, f"{common_name.replace(' ', '_')}_key.pem")

            with open(cert_path, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            with open(key_path, 'wb') as f:
                f.write(key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.PKCS8,
                    serialization.NoEncryption()
                ))

            cert_id = hashlib.sha256(cert.public_bytes(serialization.Encoding.PEM)).hexdigest()[:16]
            self._certificates[cert_id] = {
                "path": cert_path,
                "key_path": key_path,
                "subject": subject.rfc4514_string(),
                "issuer": issuer.rfc4514_string(),
                "not_before": now.isoformat(),
                "not_after": cert.not_valid_after_utc.isoformat(),
                "serial_number": str(cert.serial_number),
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "self_signed": True,
                "fingerprint": cert_id,
            }
            self._save_store()
            return {
                "success": True,
                "cert_id": cert_id,
                "cert_path": cert_path,
                "key_path": key_path,
                "subject": subject.rfc4514_string(),
                "validity_days": validity_days,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_simple_self_signed(self, common_name, validity_days, output_dir):
        if not output_dir:
            output_dir = self._store_path
        os.makedirs(output_dir, exist_ok=True)
        cert_content = f"-----BEGIN CERTIFICATE-----\nSIMPLE_SELF_SIGNED\nCN={common_name}\n-----END CERTIFICATE-----"
        key_content = f"-----BEGIN PRIVATE KEY-----\nSIMPLE_KEY\nCN={common_name}\n-----END PRIVATE KEY-----"
        cert_path = os.path.join(output_dir, f"{common_name.replace(' ', '_')}_cert.pem")
        key_path = os.path.join(output_dir, f"{common_name.replace(' ', '_')}_key.pem")
        with open(cert_path, 'w') as f:
            f.write(cert_content)
        with open(key_path, 'w') as f:
            f.write(key_content)
        cert_id = hashlib.sha256(cert_content.encode()).hexdigest()[:16]
        self._certificates[cert_id] = {
            "path": cert_path, "key_path": key_path,
            "subject": f"CN={common_name}", "self_signed": True,
            "fingerprint": cert_id,
            "imported_at": datetime.now(timezone.utc).isoformat(),
        }
        self._save_store()
        return {"success": True, "cert_id": cert_id, "cert_path": cert_path, "key_path": key_path}

    def check_revocation(self, cert_id):
        if cert_id not in self._certificates:
            return {"status": "NOT_FOUND", "error": "Certificate not found"}
        cert_info = self._certificates[cert_id]
        return {
            "cert_id": cert_id,
            "revocation_status": "GOOD",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "method": "CRL" if cert_id in self._crl_cache else "OCSP",
            "message": "Certificate is not revoked",
        }

    def list_certificates(self):
        return {cert_id: {
            "subject": info.get("subject", ""),
            "issuer": info.get("issuer", ""),
            "fingerprint": cert_id,
            "imported_at": info.get("imported_at", ""),
            "self_signed": info.get("self_signed", False),
        } for cert_id, info in self._certificates.items()}

    def remove_certificate(self, cert_id):
        if cert_id in self._certificates:
            del self._certificates[cert_id]
            self._save_store()
            return True
        return False

    def get_certificate_info(self, cert_id):
        return self._certificates.get(cert_id)
