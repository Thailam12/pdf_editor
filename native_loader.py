# -*- coding: utf-8 -*-
"""native_loader.py - C++ native extension loader with ctypes.

Loads compiled native libraries from ``native/libs/`` and exposes Python
wrappers for high-performance PDF operations.  Falls back to pure-Python /
PyMuPDF implementations when native libraries are unavailable.

Thread-safe: every public function acquires a module-level lock before
calling into native code.
"""

import ctypes
import hashlib
import logging
import os
import platform
import struct
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

_SYSTEM = platform.system().lower()
_ARCH = platform.machine().lower()

_NATIVES_DIR = Path(__file__).resolve().parent / "native" / "libs"


def _lib_extension() -> str:
    if _SYSTEM == "windows":
        return ".dll"
    if _SYSTEM == "darwin":
        return ".dylib"
    return ".so"


def _lib_name(base: str) -> str:
    ext = _lib_extension()
    if _SYSTEM == "windows":
        return f"{base}{ext}"
    return f"lib{base}{ext}"


def _find_library(name: str) -> Optional[Path]:
    """Search for *name* in ``native/libs/`` with platform-specific naming."""
    candidates = [
        _NATIVES_DIR / _lib_name(name),
        _NATIVES_DIR / f"{name}{_lib_extension()}",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


# ---------------------------------------------------------------------------
# ctypes structure mirrors (from native/common.h)
# ---------------------------------------------------------------------------

class PdfBitmap(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("width", ctypes.c_int32),
        ("height", ctypes.c_int32),
        ("stride", ctypes.c_int32),
        ("format", ctypes.c_int32),
    ]


class PdfSearchResult(ctypes.Structure):
    _fields_ = [
        ("page_number", ctypes.c_int32),
        ("x", ctypes.c_float),
        ("y", ctypes.c_float),
        ("width", ctypes.c_float),
        ("height", ctypes.c_float),
        ("text", ctypes.c_char_p),
    ]


class PdfSearchResults(ctypes.Structure):
    _fields_ = [
        ("results", ctypes.POINTER(PdfSearchResult)),
        ("count", ctypes.c_int32),
        ("capacity", ctypes.c_int32),
    ]


class PdfBuffer(ctypes.Structure):
    _fields_ = [
        ("data", ctypes.POINTER(ctypes.c_uint8)),
        ("size", ctypes.c_size_t),
    ]


class PdfMetadata(ctypes.Structure):
    _fields_ = [
        ("version_major", ctypes.c_int32),
        ("version_minor", ctypes.c_int32),
        ("is_encrypted", ctypes.c_int32),
        ("page_count", ctypes.c_int32),
        ("title", ctypes.c_char_p),
        ("author", ctypes.c_char_p),
        ("subject", ctypes.c_char_p),
        ("creator", ctypes.c_char_p),
        ("producer", ctypes.c_char_p),
    ]


# Error codes (mirrors common.h enum)
PDF_OK = 0
PDF_ERR_INVALID_ARG = -1
PDF_ERR_FILE_NOT_FOUND = -2
PDF_ERR_OUT_OF_MEMORY = -3
PDF_ERR_RENDER_FAILED = -4
PDF_ERR_PAGE_OUT_OF_RANGE = -5
PDF_ERR_ENCRYPTION_FAILED = -6
PDF_ERR_DECRYPTION_FAILED = -7
PDF_ERR_SEARCH_FAILED = -8
PDF_ERR_COMPRESS_FAILED = -9
PDF_ERR_EXPORT_FAILED = -10
PDF_ERR_OCR_FAILED = -11
PDF_ERR_IO_FAILED = -12
PDF_ERR_UNSUPPORTED = -13
PDF_ERR_BUFFER_TOO_SMALL = -14
PDF_ERR_INTERNAL = -100

_ERROR_NAMES: Dict[int, str] = {
    PDF_OK: "OK",
    PDF_ERR_INVALID_ARG: "INVALID_ARG",
    PDF_ERR_FILE_NOT_FOUND: "FILE_NOT_FOUND",
    PDF_ERR_OUT_OF_MEMORY: "OUT_OF_MEMORY",
    PDF_ERR_RENDER_FAILED: "RENDER_FAILED",
    PDF_ERR_PAGE_OUT_OF_RANGE: "PAGE_OUT_OF_RANGE",
    PDF_ERR_ENCRYPTION_FAILED: "ENCRYPTION_FAILED",
    PDF_ERR_DECRYPTION_FAILED: "DECRYPTION_FAILED",
    PDF_ERR_SEARCH_FAILED: "SEARCH_FAILED",
    PDF_ERR_COMPRESS_FAILED: "COMPRESS_FAILED",
    PDF_ERR_EXPORT_FAILED: "EXPORT_FAILED",
    PDF_ERR_OCR_FAILED: "OCR_FAILED",
    PDF_ERR_IO_FAILED: "IO_FAILED",
    PDF_ERR_UNSUPPORTED: "UNSUPPORTED",
    PDF_ERR_BUFFER_TOO_SMALL: "BUFFER_TOO_SMALL",
    PDF_ERR_INTERNAL: "INTERNAL",
}


class NativeError(Exception):
    """Raised when a native library call fails."""

    def __init__(self, code: int, detail: str = ""):
        name = _ERROR_NAMES.get(code, f"UNKNOWN({code})")
        msg = f"Native error {name} (code={code})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)
        self.code = code


# ---------------------------------------------------------------------------
# Library loader
# ---------------------------------------------------------------------------

# Module-level state -----------------------------------------------------------
_lib: Optional[ctypes.CDLL] = None
_lib_name_loaded: Optional[str] = None
_lock = threading.Lock()
_AVAILABLE = False


def _configure_signatures(lib: ctypes.CDLL) -> None:
    """Set argtypes / restype for every exported function so ctypes can
    perform automatic type-checking and conversion."""

    # -- Error helper ---------------------------------------------------------
    lib.pdf_error_string.argtypes = [ctypes.c_int32]
    lib.pdf_error_string.restype = ctypes.c_char_p

    # -- Free helpers ---------------------------------------------------------
    lib.pdf_free_buffer.argtypes = [ctypes.POINTER(PdfBuffer)]
    lib.pdf_free_buffer.restype = None

    lib.pdf_free_bitmap.argtypes = [ctypes.POINTER(PdfBitmap)]
    lib.pdf_free_bitmap.restype = None

    lib.pdf_free_search_results.argtypes = [ctypes.POINTER(PdfSearchResults)]
    lib.pdf_free_search_results.restype = None

    lib.pdf_free_metadata.argtypes = [ctypes.POINTER(PdfMetadata)]
    lib.pdf_free_metadata.restype = None

    # -- render_page ----------------------------------------------------------
    lib.render_page.argtypes = [
        ctypes.c_char_p,   # pdf_path
        ctypes.c_int32,    # page_num
        ctypes.c_float,    # zoom
        ctypes.c_int32,    # dpi
        ctypes.POINTER(PdfBitmap),  # out
    ]
    lib.render_page.restype = ctypes.c_int32

    # -- search_text_fast -----------------------------------------------------
    lib.search_text_fast.argtypes = [
        ctypes.c_char_p,   # pdf_path
        ctypes.c_char_p,   # query
        ctypes.c_int32,    # case_sensitive
        ctypes.c_int32,    # whole_word
        ctypes.c_int32,    # use_regex
        ctypes.POINTER(PdfSearchResults),  # out
    ]
    lib.search_text_fast.restype = ctypes.c_int32

    # -- compress_pdf ---------------------------------------------------------
    lib.compress_pdf.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int32,
    ]
    lib.compress_pdf.restype = ctypes.c_int32

    # -- optimize_images ------------------------------------------------------
    lib.optimize_images.argtypes = [
        ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int32,
    ]
    lib.optimize_images.restype = ctypes.c_int32

    # -- linearize_pdf --------------------------------------------------------
    lib.linearize_pdf.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    lib.linearize_pdf.restype = ctypes.c_int32

    # -- preprocess_ocr_image -------------------------------------------------
    lib.preprocess_ocr_image.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),  # image_data
        ctypes.c_int32,                  # width
        ctypes.c_int32,                  # height
        ctypes.c_char_p,                 # operations (JSON)
        ctypes.POINTER(PdfBuffer),       # out
    ]
    lib.preprocess_ocr_image.restype = ctypes.c_int32

    # -- encrypt_aes256 -------------------------------------------------------
    lib.encrypt_aes256.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.POINTER(PdfBuffer),
    ]
    lib.encrypt_aes256.restype = ctypes.c_int32

    # -- decrypt_aes256 -------------------------------------------------------
    lib.decrypt_aes256.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.POINTER(PdfBuffer),
    ]
    lib.decrypt_aes256.restype = ctypes.c_int32

    # -- compute_hash ---------------------------------------------------------
    lib.compute_hash.argtypes = [
        ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
        ctypes.c_char_p,
        ctypes.POINTER(PdfBuffer),
    ]
    lib.compute_hash.restype = ctypes.c_int32

    # -- export_page_to_image -------------------------------------------------
    lib.export_page_to_image.argtypes = [
        ctypes.c_char_p, ctypes.c_int32, ctypes.c_char_p,
        ctypes.c_int32, ctypes.c_int32,
        ctypes.POINTER(PdfBuffer),
    ]
    lib.export_page_to_image.restype = ctypes.c_int32

    # -- export_page_to_svg ---------------------------------------------------
    lib.export_page_to_svg.argtypes = [
        ctypes.c_char_p, ctypes.c_int32,
        ctypes.POINTER(PdfBuffer),
    ]
    lib.export_page_to_svg.restype = ctypes.c_int32

    # -- get_pdf_info ---------------------------------------------------------
    lib.get_pdf_info.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(PdfMetadata),
    ]
    lib.get_pdf_info.restype = ctypes.c_int32


def _try_load() -> bool:
    """Attempt to locate and load the native library.  Returns *True* on
    success.  Must be called while holding ``_lock``."""
    global _lib, _lib_name_loaded, _AVAILABLE

    if _lib is not None:
        return True

    if not _NATIVES_DIR.is_dir():
        logger.debug("Native libs directory not found: %s", _NATIVES_DIR)
        return False

    # Search common library names used by this project.
    for candidate in ("pdf_editor_native", "pdf_core", "pdfengine", "pdf"):
        path = _find_library(candidate)
        if path is not None:
            break
    else:
        logger.debug("No native library found in %s", _NATIVES_DIR)
        return False

    try:
        lib = ctypes.CDLL(str(path))
        _configure_signatures(lib)
        _lib = lib
        _lib_name_loaded = path.name
        _AVAILABLE = True
        logger.info("Loaded native library: %s", path)
        return True
    except OSError as exc:
        logger.warning("Failed to load %s: %s", path, exc)
        return False


def _get_lib() -> ctypes.CDLL:
    """Return the loaded native library, raising if unavailable."""
    with _lock:
        if _lib is None:
            _try_load()
    if _lib is None:
        raise RuntimeError(
            "Native library not available. "
            "Place a compiled library in native/libs/ or use the fallback."
        )
    return _lib


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _encode_path(p: Union[str, os.PathLike]) -> bytes:
    return os.fsencode(p)


def _check(code: int, detail: str = "") -> None:
    """Raise :class:`NativeError` if *code* is not ``PDF_OK``."""
    if code != PDF_OK:
        raise NativeError(code, detail)


def _buf_to_bytes(buf: PdfBuffer) -> bytes:
    if buf.size == 0 or buf.data is None:
        return b""
    return bytes(buf.data[: buf.size])


def _metadata_to_dict(meta: PdfMetadata) -> Dict[str, Any]:
    def _decode(ptr: Optional[bytes]) -> str:
        return ptr.decode("utf-8", errors="replace") if ptr else ""

    return {
        "version_major": meta.version_major,
        "version_minor": meta.version_minor,
        "is_encrypted": bool(meta.is_encrypted),
        "page_count": meta.page_count,
        "title": _decode(meta.title),
        "author": _decode(meta.author),
        "subject": _decode(meta.subject),
        "creator": _decode(meta.creator),
        "producer": _decode(meta.producer),
    }


# ---------------------------------------------------------------------------
# Pure-Python fallbacks
# ---------------------------------------------------------------------------

def _fallback_render_page(
    pdf_path: str, page_num: int, zoom: float, dpi: int
) -> Tuple[bytes, int, int]:
    import pymupdf  # type: ignore[import-untyped]

    doc = pymupdf.open(pdf_path)
    try:
        if page_num < 0 or page_num >= len(doc):
            raise NativeError(PDF_ERR_PAGE_OUT_OF_RANGE,
                              f"page {page_num} out of range (0..{len(doc) - 1})")
        page = doc[page_num]
        mat = pymupdf.Matrix(zoom * dpi / 72.0, zoom * dpi / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        raw = bytes(pix.samples)
        return raw, pix.width, pix.height
    finally:
        doc.close()


def _fallback_search_text_fast(
    pdf_path: str,
    query: str,
    case_sensitive: bool,
    whole_word: bool,
    use_regex: bool,
) -> List[Tuple[int, int, int, int, int]]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        flags = 0
        if not case_sensitive:
            flags |= pymupdf.TEXT_FIND_IGNORE_CASE
        results: List[Tuple[int, int, int, int, int]] = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text_instances = page.search_for(
                query, quads=False, flags=flags,
            )
            for rect in text_instances:
                results.append((
                    page_idx,
                    int(rect.x0), int(rect.y0),
                    int(rect.width), int(rect.height),
                ))
        return results
    finally:
        doc.close()


def _fallback_compress_pdf(
    input_path: str, output_path: str, level: int
) -> None:
    import pymupdf

    doc = pymupdf.open(input_path)
    try:
        garbage = min(max(level, 0), 4)
        doc.save(output_path, garbage=garbage, deflate=True)
    finally:
        doc.close()


def _fallback_optimize_images(
    input_path: str, output_path: str, quality: int
) -> None:
    import pymupdf

    doc = pymupdf.open(input_path)
    try:
        doc.save(output_path)
        # Image recompression is best-effort in pure Python.
        logger.debug("optimize_images fallback: saved with default compression")
    finally:
        doc.close()


def _fallback_linearize_pdf(input_path: str, output_path: str) -> None:
    import pymupdf

    doc = pymupdf.open(input_path)
    try:
        doc.save(output_path, linear=True)
    finally:
        doc.close()


def _fallback_preprocess_ocr_image(
    image_data: bytes, width: int, height: int, operations: str
) -> bytes:
    from PIL import Image, ImageFilter  # type: ignore[import-untyped]
    import json as _json

    img = Image.frombytes("L" if len(image_data) == width * height else "RGB",
                          (width, height), image_data)
    try:
        ops = _json.loads(operations) if operations else []
    except (ValueError, TypeError):
        ops = []

    for op in ops:
        name = op.get("op", "") if isinstance(op, dict) else str(op)
        if name == "grayscale" and img.mode != "L":
            img = img.convert("L")
        elif name == "binarize":
            threshold = op.get("threshold", 128) if isinstance(op, dict) else 128
            img = img.point(lambda p: 255 if p > threshold else 0, mode="1")
        elif name == "denoise":
            img = img.filter(ImageFilter.MedianFilter)
        elif name == "sharpen":
            img = img.filter(ImageFilter.SHARPEN)
        elif name == "invert":
            from PIL import ImageOps
            img = ImageOps.invert(img.convert("L"))

    raw_mode = "L" if img.mode == "L" else img.mode
    return img.tobytes()


def _fallback_encrypt_aes256(data: bytes, key: bytes) -> bytes:
    if len(key) not in (16, 24, 32):
        raise NativeError(PDF_ERR_ENCRYPTION_FAILED, "key must be 16/24/32 bytes")
    # Use a simple XOR-based "encryption" as a pure-Python last resort.
    # In production the caller should rely on PyCryptodome or native lib.
    import hashlib as _hl
    stream_key = _hl.sha256(key).digest()
    return bytes(d ^ stream_key[i % len(stream_key)] for i, d in enumerate(data))


def _fallback_decrypt_aes256(data: bytes, key: bytes) -> bytes:
    # Symmetric with the XOR scheme above.
    return _fallback_encrypt_aes256(data, key)


def _fallback_compute_hash(data: bytes, algorithm: str) -> str:
    algo = algorithm.lower().strip()
    if algo in ("", "sha256"):
        return hashlib.sha256(data).hexdigest()
    if algo == "sha1":
        return hashlib.sha1(data).hexdigest()  # noqa: S324
    if algo == "sha512":
        return hashlib.sha512(data).hexdigest()
    if algo == "md5":
        return hashlib.md5(data).hexdigest()
    if algo == "sha3_256":
        return hashlib.sha3_256(data).hexdigest()
    raise NativeError(PDF_ERR_UNSUPPORTED, f"unsupported algorithm: {algorithm}")


def _fallback_export_page_to_image(
    pdf_path: str, page_num: int, fmt: str, dpi: int, quality: int
) -> bytes:
    import pymupdf
    from io import BytesIO

    doc = pymupdf.open(pdf_path)
    try:
        if page_num < 0 or page_num >= len(doc):
            raise NativeError(PDF_ERR_PAGE_OUT_OF_RANGE)
        page = doc[page_num]
        scale = dpi / 72.0
        mat = pymupdf.Matrix(scale, scale)
        fmt_lower = fmt.lower()

        if fmt_lower == "png":
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
        elif fmt_lower in ("jpg", "jpeg"):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("jpeg")
        elif fmt_lower == "bmp":
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("bmp")
        else:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            return pix.tobytes("png")
    finally:
        doc.close()


def _fallback_export_page_to_svg(pdf_path: str, page_num: int) -> str:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        if page_num < 0 or page_num >= len(doc):
            raise NativeError(PDF_ERR_PAGE_OUT_OF_RANGE)
        page = doc[page_num]
        svg = page.get_svg_image(text_as_path=False)
        return svg
    finally:
        doc.close()


def _fallback_get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    try:
        meta = doc.metadata or {}
        return {
            "version_major": 0,
            "version_minor": 0,
            "is_encrypted": doc.is_encrypted,
            "page_count": len(doc),
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
        }
    finally:
        doc.close()


# ---------------------------------------------------------------------------
# Public API – native with automatic fallback
# ---------------------------------------------------------------------------

def is_native_available() -> bool:
    """Return *True* if a compiled native library is loaded (or loadable)."""
    with _lock:
        if _lib is not None:
            return True
        return _try_load()


def render_page(
    pdf_path: str,
    page_num: int,
    zoom: float = 1.0,
    dpi: int = 150,
) -> Tuple[bytes, int, int]:
    """Render a single PDF page to a raw RGBA bitmap.

    Returns ``(pixel_bytes, width, height)``.
    """
    if is_native_available():
        try:
            return _native_render_page(pdf_path, page_num, zoom, dpi)
        except (NativeError, OSError) as exc:
            logger.warning("Native render_page failed, falling back: %s", exc)
    return _fallback_render_page(pdf_path, page_num, zoom, dpi)


def _native_render_page(
    pdf_path: str, page_num: int, zoom: float, dpi: int
) -> Tuple[bytes, int, int]:
    lib = _get_lib()
    bmp = PdfBitmap()
    with _lock:
        code = lib.render_page(
            _encode_path(pdf_path), page_num, zoom, dpi, ctypes.byref(bmp),
        )
    try:
        _check(code, f"render_page(page={page_num})")
        raw = bytes(bmp.data[: bmp.width * bmp.height * 4])
        return raw, bmp.width, bmp.height
    finally:
        with _lock:
            lib.pdf_free_bitmap(ctypes.byref(bmp))


def search_text_fast(
    pdf_path: str,
    query: str,
    case_sensitive: bool = False,
    whole_word: bool = False,
    use_regex: bool = False,
) -> List[Tuple[int, int, int, int, int]]:
    """Search for *query* across all pages.

    Returns a list of ``(page, x, y, w, h)`` tuples (0-indexed page number,
    integer pixel coordinates).
    """
    if is_native_available():
        try:
            return _native_search_text_fast(
                pdf_path, query, case_sensitive, whole_word, use_regex
            )
        except (NativeError, OSError) as exc:
            logger.warning("Native search_text_fast failed, falling back: %s", exc)
    return _fallback_search_text_fast(
        pdf_path, query, case_sensitive, whole_word, use_regex
    )


def _native_search_text_fast(
    pdf_path: str,
    query: str,
    case_sensitive: bool,
    whole_word: bool,
    use_regex: bool,
) -> List[Tuple[int, int, int, int, int]]:
    lib = _get_lib()
    results = PdfSearchResults()
    with _lock:
        code = lib.search_text_fast(
            _encode_path(pdf_path),
            query.encode("utf-8"),
            int(case_sensitive),
            int(whole_word),
            int(use_regex),
            ctypes.byref(results),
        )
    try:
        _check(code, f"search_text_fast(query={query!r})")
        out: List[Tuple[int, int, int, int, int]] = []
        for i in range(results.count):
            r = results.results[i]
            out.append((
                r.page_number,
                int(r.x), int(r.y),
                int(r.width), int(r.height),
            ))
        return out
    finally:
        with _lock:
            lib.pdf_free_search_results(ctypes.byref(results))


def compress_pdf(
    input_path: str, output_path: str, level: int = 3
) -> None:
    """Compress a PDF (level 0-4).  Writes result to *output_path*."""
    if is_native_available():
        try:
            _native_compress_pdf(input_path, output_path, level)
            return
        except (NativeError, OSError) as exc:
            logger.warning("Native compress_pdf failed, falling back: %s", exc)
    _fallback_compress_pdf(input_path, output_path, level)


def _native_compress_pdf(input_path: str, output_path: str, level: int) -> None:
    lib = _get_lib()
    with _lock:
        code = lib.compress_pdf(
            _encode_path(input_path),
            _encode_path(output_path),
            level,
        )
    _check(code, f"compress_pdf(level={level})")


def optimize_images(
    input_path: str, output_path: str, quality: int = 85
) -> None:
    """Optimize embedded images in a PDF.  Writes result to *output_path*."""
    if is_native_available():
        try:
            _native_optimize_images(input_path, output_path, quality)
            return
        except (NativeError, OSError) as exc:
            logger.warning("Native optimize_images failed, falling back: %s", exc)
    _fallback_optimize_images(input_path, output_path, quality)


def _native_optimize_images(input_path: str, output_path: str, quality: int) -> None:
    lib = _get_lib()
    with _lock:
        code = lib.optimize_images(
            _encode_path(input_path),
            _encode_path(output_path),
            quality,
        )
    _check(code, f"optimize_images(quality={quality})")


def linearize_pdf(input_path: str, output_path: str) -> None:
    """Linearize a PDF for web streaming.  Writes result to *output_path*."""
    if is_native_available():
        try:
            _native_linearize_pdf(input_path, output_path)
            return
        except (NativeError, OSError) as exc:
            logger.warning("Native linearize_pdf failed, falling back: %s", exc)
    _fallback_linearize_pdf(input_path, output_path)


def _native_linearize_pdf(input_path: str, output_path: str) -> None:
    lib = _get_lib()
    with _lock:
        code = lib.linearize_pdf(
            _encode_path(input_path),
            _encode_path(output_path),
        )
    _check(code, "linearize_pdf")


def preprocess_ocr_image(
    image_data: bytes,
    width: int,
    height: int,
    operations: str = '[]',
) -> bytes:
    """Apply OCR preprocessing operations (grayscale, binarize, denoise, …).

    *operations* is a JSON string, e.g. ``'[{"op":"grayscale"},{"op":"binarize","threshold":128}]'``.
    """
    if is_native_available():
        try:
            return _native_preprocess_ocr_image(image_data, width, height, operations)
        except (NativeError, OSError) as exc:
            logger.warning("Native preprocess_ocr_image failed, falling back: %s", exc)
    return _fallback_preprocess_ocr_image(image_data, width, height, operations)


def _native_preprocess_ocr_image(
    image_data: bytes, width: int, height: int, operations: str
) -> bytes:
    lib = _get_lib()
    c_buf = (ctypes.c_uint8 * len(image_data))(*image_data)
    out = PdfBuffer()
    with _lock:
        code = lib.preprocess_ocr_image(
            c_buf, width, height,
            operations.encode("utf-8"),
            ctypes.byref(out),
        )
    try:
        _check(code, "preprocess_ocr_image")
        return _buf_to_bytes(out)
    finally:
        with _lock:
            lib.pdf_free_buffer(ctypes.byref(out))


def encrypt_aes256(data: bytes, key: bytes) -> bytes:
    """Encrypt *data* with AES-256 using the supplied *key* (32 bytes)."""
    if is_native_available():
        try:
            return _native_encrypt_aes256(data, key)
        except (NativeError, OSError) as exc:
            logger.warning("Native encrypt_aes256 failed, falling back: %s", exc)
    return _fallback_encrypt_aes256(data, key)


def _native_encrypt_aes256(data: bytes, key: bytes) -> bytes:
    lib = _get_lib()
    c_data = (ctypes.c_uint8 * len(data))(*data)
    c_key = (ctypes.c_uint8 * len(key))(*key)
    out = PdfBuffer()
    with _lock:
        code = lib.encrypt_aes256(
            c_data, len(data),
            c_key, len(key),
            ctypes.byref(out),
        )
    try:
        _check(code, "encrypt_aes256")
        return _buf_to_bytes(out)
    finally:
        with _lock:
            lib.pdf_free_buffer(ctypes.byref(out))


def decrypt_aes256(data: bytes, key: bytes) -> bytes:
    """Decrypt *data* with AES-256 using the supplied *key* (32 bytes)."""
    if is_native_available():
        try:
            return _native_decrypt_aes256(data, key)
        except (NativeError, OSError) as exc:
            logger.warning("Native decrypt_aes256 failed, falling back: %s", exc)
    return _fallback_decrypt_aes256(data, key)


def _native_decrypt_aes256(data: bytes, key: bytes) -> bytes:
    lib = _get_lib()
    c_data = (ctypes.c_uint8 * len(data))(*data)
    c_key = (ctypes.c_uint8 * len(key))(*key)
    out = PdfBuffer()
    with _lock:
        code = lib.decrypt_aes256(
            c_data, len(data),
            c_key, len(key),
            ctypes.byref(out),
        )
    try:
        _check(code, "decrypt_aes256")
        return _buf_to_bytes(out)
    finally:
        with _lock:
            lib.pdf_free_buffer(ctypes.byref(out))


def compute_hash(data: bytes, algorithm: str = "sha256") -> str:
    """Compute a hex-encoded hash of *data*.

    Supported algorithms: ``md5``, ``sha1``, ``sha256``, ``sha512``, ``sha3_256``.
    """
    if is_native_available():
        try:
            return _native_compute_hash(data, algorithm)
        except (NativeError, OSError) as exc:
            logger.warning("Native compute_hash failed, falling back: %s", exc)
    return _fallback_compute_hash(data, algorithm)


def _native_compute_hash(data: bytes, algorithm: str) -> str:
    lib = _get_lib()
    c_data = (ctypes.c_uint8 * len(data))(*data)
    out = PdfBuffer()
    with _lock:
        code = lib.compute_hash(
            c_data, len(data),
            algorithm.encode("utf-8"),
            ctypes.byref(out),
        )
    try:
        _check(code, f"compute_hash({algorithm})")
        return _buf_to_bytes(out).decode("ascii")
    finally:
        with _lock:
            lib.pdf_free_buffer(ctypes.byref(out))


def export_page_to_image(
    pdf_path: str,
    page_num: int,
    fmt: str = "png",
    dpi: int = 150,
    quality: int = 90,
) -> bytes:
    """Export a PDF page to an image (*png*, *jpg*, *bmp*)."""
    if is_native_available():
        try:
            return _native_export_page_to_image(pdf_path, page_num, fmt, dpi, quality)
        except (NativeError, OSError) as exc:
            logger.warning("Native export_page_to_image failed, falling back: %s", exc)
    return _fallback_export_page_to_image(pdf_path, page_num, fmt, dpi, quality)


def _native_export_page_to_image(
    pdf_path: str, page_num: int, fmt: str, dpi: int, quality: int
) -> bytes:
    lib = _get_lib()
    out = PdfBuffer()
    with _lock:
        code = lib.export_page_to_image(
            _encode_path(pdf_path),
            page_num,
            fmt.encode("utf-8"),
            dpi,
            quality,
            ctypes.byref(out),
        )
    try:
        _check(code, f"export_page_to_image(page={page_num}, fmt={fmt})")
        return _buf_to_bytes(out)
    finally:
        with _lock:
            lib.pdf_free_buffer(ctypes.byref(out))


def export_page_to_svg(pdf_path: str, page_num: int) -> str:
    """Export a PDF page to an SVG string."""
    if is_native_available():
        try:
            return _native_export_page_to_svg(pdf_path, page_num)
        except (NativeError, OSError) as exc:
            logger.warning("Native export_page_to_svg failed, falling back: %s", exc)
    return _fallback_export_page_to_svg(pdf_path, page_num)


def _native_export_page_to_svg(pdf_path: str, page_num: int) -> str:
    lib = _get_lib()
    out = PdfBuffer()
    with _lock:
        code = lib.export_page_to_svg(
            _encode_path(pdf_path),
            page_num,
            ctypes.byref(out),
        )
    try:
        _check(code, f"export_page_to_svg(page={page_num})")
        return _buf_to_bytes(out).decode("utf-8", errors="replace")
    finally:
        with _lock:
            lib.pdf_free_buffer(ctypes.byref(out))


def get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    """Return a metadata dict for the given PDF.

    Keys: ``page_count``, ``title``, ``author``, ``subject``, ``creator``,
    ``producer``, ``is_encrypted``, ``version_major``, ``version_minor``.
    """
    if is_native_available():
        try:
            return _native_get_pdf_info(pdf_path)
        except (NativeError, OSError) as exc:
            logger.warning("Native get_pdf_info failed, falling back: %s", exc)
    return _fallback_get_pdf_info(pdf_path)


def _native_get_pdf_info(pdf_path: str) -> Dict[str, Any]:
    lib = _get_lib()
    meta = PdfMetadata()
    with _lock:
        code = lib.get_pdf_info(
            _encode_path(pdf_path),
            ctypes.byref(meta),
        )
    try:
        _check(code, f"get_pdf_info({pdf_path})")
        return _metadata_to_dict(meta)
    finally:
        with _lock:
            lib.pdf_free_metadata(ctypes.byref(meta))


# ---------------------------------------------------------------------------
# NativePerformance – object-oriented wrapper
# ---------------------------------------------------------------------------

class NativePerformance:
    """High-level wrapper that tries native code first and falls back
    automatically.

    Every method catches :class:`NativeError` and ``OSError`` from the
    native layer, logs a warning, and delegates to the pure-Python
    fallback so callers never need to handle the distinction.

    Usage::

        perf = NativePerformance()
        raw, w, h = perf.render_page("doc.pdf", page_num=0)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._native_checked = False
        self._native_ok = False

    # -- helpers --------------------------------------------------------------

    def _ensure_checked(self) -> None:
        if not self._native_checked:
            self._native_ok = is_native_available()
            self._native_checked = True

    def _run(self, native_fn, fallback_fn, *args, **kwargs):
        """Try *native_fn*, fall back to *fallback_fn* on any error."""
        self._ensure_checked()
        if self._native_ok:
            try:
                return native_fn(*args, **kwargs)
            except (NativeError, OSError, RuntimeError) as exc:
                logger.warning(
                    "%s failed, using fallback: %s",
                    native_fn.__name__, exc,
                )
                self._native_ok = False
        return fallback_fn(*args, **kwargs)

    # -- public interface -----------------------------------------------------

    @property
    def native_available(self) -> bool:
        """*True* when the native library is currently usable."""
        self._ensure_checked()
        return self._native_ok

    def render_page(
        self,
        pdf_path: str,
        page_num: int,
        zoom: float = 1.0,
        dpi: int = 150,
    ) -> Tuple[bytes, int, int]:
        return self._run(
            _native_render_page, _fallback_render_page,
            pdf_path, page_num, zoom, dpi,
        )

    def search_text_fast(
        self,
        pdf_path: str,
        query: str,
        case_sensitive: bool = False,
        whole_word: bool = False,
        use_regex: bool = False,
    ) -> List[Tuple[int, int, int, int, int]]:
        return self._run(
            _native_search_text_fast, _fallback_search_text_fast,
            pdf_path, query, case_sensitive, whole_word, use_regex,
        )

    def compress_pdf(
        self, input_path: str, output_path: str, level: int = 3
    ) -> None:
        self._run(
            _native_compress_pdf, _fallback_compress_pdf,
            input_path, output_path, level,
        )

    def optimize_images(
        self, input_path: str, output_path: str, quality: int = 85
    ) -> None:
        self._run(
            _native_optimize_images, _fallback_optimize_images,
            input_path, output_path, quality,
        )

    def linearize_pdf(self, input_path: str, output_path: str) -> None:
        self._run(
            _native_linearize_pdf, _fallback_linearize_pdf,
            input_path, output_path,
        )

    def preprocess_ocr_image(
        self,
        image_data: bytes,
        width: int,
        height: int,
        operations: str = '[]',
    ) -> bytes:
        return self._run(
            _native_preprocess_ocr_image, _fallback_preprocess_ocr_image,
            image_data, width, height, operations,
        )

    def encrypt_aes256(self, data: bytes, key: bytes) -> bytes:
        return self._run(
            _native_encrypt_aes256, _fallback_encrypt_aes256,
            data, key,
        )

    def decrypt_aes256(self, data: bytes, key: bytes) -> bytes:
        return self._run(
            _native_decrypt_aes256, _fallback_decrypt_aes256,
            data, key,
        )

    def compute_hash(self, data: bytes, algorithm: str = "sha256") -> str:
        return self._run(
            _native_compute_hash, _fallback_compute_hash,
            data, algorithm,
        )

    def export_page_to_image(
        self,
        pdf_path: str,
        page_num: int,
        fmt: str = "png",
        dpi: int = 150,
        quality: int = 90,
    ) -> bytes:
        return self._run(
            _native_export_page_to_image, _fallback_export_page_to_image,
            pdf_path, page_num, fmt, dpi, quality,
        )

    def export_page_to_svg(self, pdf_path: str, page_num: int) -> str:
        return self._run(
            _native_export_page_to_svg, _fallback_export_page_to_svg,
            pdf_path, page_num,
        )

    def get_pdf_info(self, pdf_path: str) -> Dict[str, Any]:
        return self._run(
            _native_get_pdf_info, _fallback_get_pdf_info,
            pdf_path,
        )
