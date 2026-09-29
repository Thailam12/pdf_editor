"""Local-only productivity features for PDFMind.

All operations in this module use local files and the Python standard library,
with pypdf used only for PDF metadata and text extraction.
"""

import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APP_VERSION = "2026.6"


def sha256_file(path: str) -> str:
    """Return the SHA-256 digest of a local file."""
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_text(path: str) -> str:
    """Extract all page text locally using pypdf."""
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            pages.append(f"--- Page {page_number} ---\n{text}")
    return "\n\n".join(pages)


def inspect_pdfs(paths: list[str]) -> list[dict[str, Any]]:
    """Return local metadata for a group of PDF files."""
    from pypdf import PdfReader

    results = []
    for path in paths:
        file_path = Path(path)
        item: dict[str, Any] = {
            "file": str(file_path),
            "exists": file_path.is_file(),
        }
        if not file_path.is_file():
            item["error"] = "File not found"
            results.append(item)
            continue
        try:
            reader = PdfReader(str(file_path))
            item.update({
                "size_bytes": file_path.stat().st_size,
                "pages": len(reader.pages),
                "encrypted": reader.is_encrypted,
                "sha256": sha256_file(str(file_path)),
            })
        except Exception as error:
            item["error"] = str(error)
        results.append(item)
    return results


class LocalHistory:
    """Store versioned PDF snapshots in the user's local data directory."""

    def __init__(self, root: str | None = None):
        base = Path(root) if root else Path.home() / ".pdfmind" / "history"
        self.root = base

    def snapshot(self, source: str) -> Path:
        source_path = Path(source).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(source)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        document_dir = self.root / source_path.stem
        document_dir.mkdir(parents=True, exist_ok=True)
        destination = document_dir / f"{timestamp}_{source_path.name}"
        shutil.copy2(source_path, destination)
        metadata = {
            "source": str(source_path),
            "snapshot": str(destination),
            "created_utc": timestamp,
            "sha256": sha256_file(str(destination)),
        }
        destination.with_suffix(destination.suffix + ".json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        return destination

    def list_snapshots(self, source: str) -> list[dict[str, Any]]:
        document_dir = self.root / Path(source).stem
        snapshots = []
        for snapshot in sorted(document_dir.glob("*.pdf"), reverse=True):
            snapshots.append({
                "file": str(snapshot),
                "size_bytes": snapshot.stat().st_size,
                "sha256": sha256_file(str(snapshot)),
            })
        return snapshots


def diagnostics() -> dict[str, Any]:
    """Report local runtime capabilities without making network requests."""
    dependencies = {}
    for name in ("fitz", "pypdf", "PIL", "torch", "onnxruntime"):
        try:
            __import__(name)
            dependencies[name] = True
        except ImportError:
            dependencies[name] = False
    return {
        "app": "pdfmind",
        "version": APP_VERSION,
        "mode": "local",
        "network_requests": False,
        "python": platform.python_version(),
        "platform": sys.platform,
        "dependencies": dependencies,
        "history_directory": str(Path.home() / ".pdfmind" / "history"),
    }
