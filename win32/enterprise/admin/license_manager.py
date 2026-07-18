"""Feature flags manager — controls which features are enabled or disabled."""

import os
import json


DEFAULT_FEATURES = {
    "basic_edit": True,
    "view": True,
    "print": True,
    "annotate": True,
    "forms": True,
    "ocr": True,
    "compress": True,
    "export": True,
    "redact": True,
    "bates": True,
    "sign": True,
    "encrypt": True,
    "compare": True,
    "spellcheck": True,
    "tts": True,
    "measurement": True,
    "pdfa": True,
    "accessibility": True,
    "sso": True,
    "admin_console": True,
    "sharepoint": True,
    "onedrive": True,
    "compliance": True,
}


class FeatureFlagManager:
    def __init__(self, data_dir=None):
        self._data_dir = data_dir or os.path.join(os.path.expanduser("~"), ".pdf_editor", "features")
        os.makedirs(self._data_dir, exist_ok=True)
        self._flags = dict(DEFAULT_FEATURES)
        self._load_flags()

    def _flags_file(self):
        return os.path.join(self._data_dir, "flags.json")

    def _load_flags(self):
        path = self._flags_file()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    saved = json.load(f)
                    self._flags.update(saved)
            except Exception:
                pass

    def _save_flags(self):
        try:
            with open(self._flags_file(), 'w') as f:
                json.dump(self._flags, f, indent=2)
        except Exception:
            pass

    def is_enabled(self, feature_name):
        return self._flags.get(feature_name, False)

    def enable(self, feature_name):
        self._flags[feature_name] = True
        self._save_flags()
        return {"success": True, "feature": feature_name, "enabled": True}

    def disable(self, feature_name):
        self._flags[feature_name] = False
        self._save_flags()
        return {"success": True, "feature": feature_name, "enabled": False}

    def set_flag(self, feature_name, enabled):
        self._flags[feature_name] = bool(enabled)
        self._save_flags()
        return {"success": True, "feature": feature_name, "enabled": bool(enabled)}

    def get_all_flags(self):
        return dict(self._flags)

    def get_enabled_features(self):
        return [name for name, enabled in self._flags.items() if enabled]

    def get_disabled_features(self):
        return [name for name, enabled in self._flags.items() if not enabled]

    def reset_to_defaults(self):
        self._flags = dict(DEFAULT_FEATURES)
        self._save_flags()
        return {"success": True, "flags": self.get_all_flags()}

    def check_feature(self, feature_name):
        return self.is_enabled(feature_name)

    def get_feature_info(self):
        return {
            "total_features": len(self._flags),
            "enabled": len(self.get_enabled_features()),
            "disabled": len(self.get_disabled_features()),
            "flags": self.get_all_flags(),
        }
