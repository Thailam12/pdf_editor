# -*- coding: utf-8 -*-
"""Native library loader.

Detects and loads native dependencies (Tesseract OCR, Poppler, etc.)
with graceful fallbacks when libraries are not installed.
"""
import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_LIBRARY_STATUS: Dict[str, Dict[str, Any]] = {}


def _find_executable(name: str) -> Optional[str]:
    """Find an executable on PATH."""
    path = shutil.which(name)
    if path:
        return str(Path(path).resolve())
    return None


def _find_tesseract() -> Optional[str]:
    """Locate Tesseract OCR binary."""
    candidates = ["tesseract", "tesseract.exe"]
    for name in candidates:
        result = _find_executable(name)
        if result:
            return result
    win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.isfile(win_path):
        return win_path
    return None


def _find_poppler() -> Optional[str]:
    """Locate Poppler pdftoppm / pdfinfo binaries."""
    for name in ("pdftoppm", "pdftoppm.exe", "pdfinfo", "pdfinfo.exe"):
        result = _find_executable(name)
        if result:
            return str(Path(result).parent)
    win_path = r"C:\Program Files\poppler\Library\bin"
    if os.path.isdir(win_path):
        return win_path
    return None


def _find_ghostscript() -> Optional[str]:
    """Locate Ghostscript binary."""
    for name in ("gs", "gswin64c", "gswin64c.exe", "gswin32c", "gswin32c.exe"):
        result = _find_executable(name)
        if result:
            return result
    for version in ("gs10.02.1", "gs10.01.4", "gs9.56.1"):
        for prog in ("gswin64c.exe", "gswin32c.exe"):
            candidate = rf"C:\Program Files\gs\{version}\bin\{prog}"
            if os.path.isfile(candidate):
                return candidate
    return None


def _check_pymupdf() -> bool:
    """Check if PyMuPDF is available."""
    try:
        import pymupdf
        return True
    except ImportError:
        return False


def _check_pillow() -> bool:
    """Check if Pillow is available."""
    try:
        from PIL import Image
        return True
    except ImportError:
        return False


def _check_pytesseract() -> bool:
    """Check if pytesseract Python package is available."""
    try:
        import pytesseract
        return True
    except ImportError:
        return False


def _check_reportlab() -> bool:
    """Check if reportlab is available."""
    try:
        import reportlab
        return True
    except ImportError:
        return False


def detect_all() -> Dict[str, Dict[str, Any]]:
    """Detect all native libraries and return status dict."""
    global _LIBRARY_STATUS

    tesseract_bin = _find_tesseract()
    poppler_dir = _find_poppler()
    gs_bin = _find_ghostscript()

    _LIBRARY_STATUS = {
        "pymupdf": {
            "available": _check_pymupdf(),
            "type": "python",
            "description": "PDF rendering and manipulation",
        },
        "pillow": {
            "available": _check_pillow(),
            "type": "python",
            "description": "Image processing",
        },
        "reportlab": {
            "available": _check_reportlab(),
            "type": "python",
            "description": "PDF generation",
        },
        "tesseract": {
            "available": tesseract_bin is not None,
            "type": "native",
            "path": tesseract_bin,
            "description": "OCR engine",
        },
        "pytesseract": {
            "available": _check_pytesseract(),
            "type": "python",
            "description": "Tesseract Python wrapper",
        },
        "poppler": {
            "available": poppler_dir is not None,
            "type": "native",
            "path": poppler_dir,
            "description": "PDF utilities (pdftoppm, pdfinfo)",
        },
        "ghostscript": {
            "available": gs_bin is not None,
            "type": "native",
            "path": gs_bin,
            "description": "PDF/PS interpreter",
        },
    }
    return _LIBRARY_STATUS


def get_status(library: str) -> Optional[Dict[str, Any]]:
    """Get status of a specific library."""
    if not _LIBRARY_STATUS:
        detect_all()
    return _LIBRARY_STATUS.get(library)


def is_available(library: str) -> bool:
    """Check if a specific library is available."""
    status = get_status(library)
    if status is None:
        return False
    return status.get("available", False)


def get_missing() -> list:
    """Return list of missing libraries."""
    if not _LIBRARY_STATUS:
        detect_all()
    return [
        name
        for name, info in _LIBRARY_STATUS.items()
        if not info.get("available", False)
    ]


def print_status():
    """Print library status to stdout."""
    if not _LIBRARY_STATUS:
        detect_all()

    print("\n  PDFMind AI — Native Library Status\n")
    print(f"  {'Library':<15} {'Status':<10} {'Type':<8} {'Description'}")
    print(f"  {'-'*15} {'-'*10} {'-'*8} {'-'*30}")
    for name, info in _LIBRARY_STATUS.items():
        status = "OK" if info["available"] else "MISSING"
        lib_type = info.get("type", "unknown")
        desc = info.get("description", "")
        path_note = ""
        if info.get("path"):
            path_note = f" ({info['path']})"
        print(f"  {name:<15} {status:<10} {lib_type:<8} {desc}{path_note}")

    missing = get_missing()
    if missing:
        print(f"\n  Missing: {', '.join(missing)}")
        print("  Install with: pip install -r requirements.txt")
    else:
        print("\n  All libraries available!")
    print()


def configure_pytesseract():
    """Configure pytesseract to find the Tesseract binary."""
    if not _LIBRARY_STATUS:
        detect_all()
    tesseract_info = _LIBRARY_STATUS.get("tesseract", {})
    tesseract_path = tesseract_info.get("path")
    if tesseract_path:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            logger.info(f"Tesseract configured: {tesseract_path}")
        except ImportError:
            logger.warning("pytesseract not installed, cannot configure Tesseract path")


def ensure_minimum():
    """Ensure minimum required libraries are available.

    Returns True if all required libraries are present.
    Raises RuntimeError with helpful message if not.
    """
    if not _LIBRARY_STATUS:
        detect_all()

    required = ["pymupdf", "pillow"]
    missing_required = [r for r in required if not is_available(r)]

    if missing_required:
        raise RuntimeError(
            f"Required libraries missing: {', '.join(missing_required)}\n"
            f"Install with: pip install -r requirements.txt"
        )

    optional_warn = ["tesseract", "poppler"]
    missing_optional = [o for o in optional_warn if not is_available(o)]
    if missing_optional:
        logger.warning(
            f"Optional libraries not found: {', '.join(missing_optional)}. "
            f"Some features (OCR, PDF-to-image) may be limited."
        )

    return True


if __name__ == "__main__":
    print_status()
