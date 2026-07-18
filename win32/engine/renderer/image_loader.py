"""Image decoding, conversion, and thumbnail generation for PDF images.

Handles JPEG, PNG, TIFF, CCITT, JBIG2, and JPX (JPEG 2000) formats with
color space conversion, downsampling, EXIF extraction, and alpha handling.
"""

from __future__ import annotations

import io
import logging
import struct
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from PIL import Image, ExifTags
from PIL import ImageFilter

logger = logging.getLogger(__name__)


class ImageFormat(Enum):
    """Detected image formats."""
    UNKNOWN = auto()
    JPEG = auto()
    PNG = auto()
    TIFF = auto()
    BMP = auto()
    CCITT = auto()
    JBIG2 = auto()
    JPX = auto()
    RAW = auto()
    GIF = auto()


class ColorSpaceType(Enum):
    """Color space classification."""
    GRAYSCALE = auto()
    RGB = auto()
    CMYK = auto()
    LAB = auto()
    CALRGB = auto()
    ICC_BASED = auto()
    SEPARATION = auto()
    DEVICE_N = auto()
    INDEXED = auto()
    UNKNOWN = auto()


@dataclass
class ImageMetadata:
    """Metadata extracted from an image."""
    format: ImageFormat = ImageFormat.UNKNOWN
    width: int = 0
    height: int = 0
    bits_per_component: int = 8
    color_space: ColorSpaceType = ColorSpaceType.UNKNOWN
    color_space_name: str = ""
    has_alpha: bool = False
    dpi: Tuple[float, float] = (72.0, 72.0)
    icc_profile: Optional[bytes] = None
    exif_data: Dict[str, Any] = field(default_factory=dict)
    compression: str = ""
    filters: List[str] = field(default_factory=list)


@dataclass
class DecodedImage:
    """A fully decoded and optionally converted image."""
    image: Image.Image
    metadata: ImageMetadata
    original_bytes: Optional[bytes] = None

    @property
    def size(self) -> Tuple[int, int]:
        return self.image.size

    @property
    def mode(self) -> str:
        return self.image.mode

    def to_rgb(self) -> Image.Image:
        if self.image.mode == "RGB":
            return self.image
        if self.image.mode == "CMYK":
            return cmyk_to_rgb(self.image)
        if self.image.mode == "L":
            return self.image.convert("RGB")
        if self.image.mode == "LA":
            return self.image.convert("RGB")
        if self.image.mode == "RGBA":
            return self.image.convert("RGB")
        if self.image.mode == "P":
            return self.image.convert("RGB")
        return self.image.convert("RGB")

    def to_rgba(self) -> Image.Image:
        if self.image.mode == "RGBA":
            return self.image
        return self.image.convert("RGBA")

    def resize(self, width: int, height: int, resample: int = Image.LANCZOS) -> Image.Image:
        return self.image.resize((width, height), resample)

    def thumbnail(self, max_width: int, max_height: int) -> Image.Image:
        img = self.image.copy()
        img.thumbnail((max_width, max_height), Image.LANCZOS)
        return img


# --- Format Detection ---

JPEG_SIGNATURES = (b"\xff\xd8\xff",)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TIFF_LE_SIGNATURE = b"II\x2a\x00"
TIFF_BE_SIGNATURE = b"MM\x00\x2a"
BMP_SIGNATURE = b"BM"
GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
JBIG2_SIGNATURE = b"\x97\x4a\x42\x32\x0d\x0a\x1a\x0a"
JPX_SIGNATURE = b"\x00\x00\x00\x0c\x6a\x50\x20\x20\x0d\x0a\x87\x0a"


def detect_image_format(data: bytes) -> ImageFormat:
    """Detect image format from raw bytes by examining magic numbers."""
    if len(data) < 12:
        return ImageFormat.UNKNOWN

    if data[:3] in JPEG_SIGNATURES:
        return ImageFormat.JPEG
    if data[:8] == PNG_SIGNATURE:
        return ImageFormat.PNG
    if data[:4] == TIFF_LE_SIGNATURE or data[:4] == TIFF_BE_SIGNATURE:
        return ImageFormat.TIFF
    if data[:2] == BMP_SIGNATURE:
        return ImageFormat.BMP
    if data[:6] in GIF_SIGNATURES:
        return ImageFormat.GIF
    if data[:8] == JBIG2_SIGNATURE:
        return ImageFormat.JBIG2
    if data[:12] == JPX_SIGNATURE:
        return ImageFormat.JPX

    if len(data) > 100 and _looks_like_ccitt(data):
        return ImageFormat.CCITT

    return ImageFormat.UNKNOWN


def _looks_like_ccitt(data: bytes) -> bool:
    """Heuristic check for CCITT fax compressed data."""
    if len(data) < 20:
        return False
    ccitt_patterns = (b"\x00", b"\xff", b"\x00\x00")
    match_count = sum(1 for p in ccitt_patterns if p in data[:50])
    return match_count >= 2 and data[0:2] in (b"\x00\x00", b"\xff\x00")


# --- EXIF Extraction ---

def extract_exif(data: bytes) -> Dict[str, Any]:
    """Extract EXIF metadata from image bytes.

    Returns a dictionary of human-readable EXIF tag names to values.
    Only works for JPEG and TIFF images with embedded EXIF.
    """
    result: Dict[str, Any] = {}
    try:
        img = Image.open(io.BytesIO(data))
        exif_data = img.getexif()
        if not exif_data:
            return result

        for tag_id, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = str(value)[:100]
            elif isinstance(value, tuple):
                value = tuple(
                    float(v) if isinstance(v, (int, float)) else v for v in value
                )
            result[tag_name] = value

        if hasattr(img, "_getexif") and img._getexif is not None:
            gps_info = exif_data.get(0x8825)
            if gps_info:
                result["GPSInfo"] = _parse_gps(gps_info)

    except Exception as e:
        logger.debug("EXIF extraction failed: %s", e)

    return result


def _parse_gps(gps_data: Any) -> Dict[str, Any]:
    """Parse GPS IFD tag into readable dict."""
    if not isinstance(gps_data, dict):
        return {}
    gps: Dict[str, Any] = {}
    for key, val in gps_data.items():
        tag = ExifTags.GPSTAGS.get(key, str(key))
        gps[tag] = val
    return gps


# --- Color Space Conversion ---

def cmyk_to_rgb(image: Image.Image) -> Image.Image:
    """Convert CMYK image to RGB using naive formula.

    For production ICC-based conversion, the ICC profile should be used.
    This is a reasonable approximation for on-screen preview.
    """
    if image.mode != "CMYK":
        return image.convert("RGB")

    r, g, b, _ = image.split()
    r = r.point(lambda x: 255 - x)
    g = g.point(lambda x: 255 - x)
    b = b.point(lambda x: 255 - x)
    return Image.merge("RGB", (r, g, b))


def cmyk_to_rgb_array(
    cmyk_values: Tuple[float, float, float, float],
) -> Tuple[int, int, int]:
    """Convert CMYK values (0-1 each) to RGB (0-255 each)."""
    c, m, y, k = cmyk_values
    r = 255 * (1 - c) * (1 - k)
    g = 255 * (1 - m) * (1 - k)
    b = 255 * (1 - y) * (1 - k)
    return (int(r), int(g), int(b))


def gray_to_rgb(value: int) -> Tuple[int, int, int]:
    """Convert grayscale value to RGB tuple."""
    v = max(0, min(255, value))
    return (v, v, v)


def lab_to_xyz(
    l_val: float, a_val: float, b_val: float
) -> Tuple[float, float, float]:
    """Convert CIE L*a*b* to CIE XYZ."""
    fy = (l_val + 16.0) / 116.0
    fx = a_val / 500.0 + fy
    fz = fy - b_val / 200.0

    def _inv(t: float) -> float:
        delta = 6.0 / 29.0
        if t > delta:
            return t ** 3
        return 3 * delta ** 2 * (t - 4.0 / 29.0)

    x = _inv(fx) * 0.95047
    y = _inv(fy) * 1.0
    z = _inv(fz) * 1.08883
    return (x, y, z)


def xyz_to_rgb(
    x: float, y: float, z: float
) -> Tuple[int, int, int]:
    """Convert CIE XYZ (0-1) to sRGB (0-255)."""
    r = x * 3.2406 + y * -1.5372 + z * -0.4986
    g = x * -0.9689 + y * 1.8758 + z * 0.0415
    b = x * 0.0557 + y * -0.2040 + z * 1.0570

    def _gamma(c: float) -> float:
        if c <= 0.0031308:
            return 12.92 * c
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

    r = max(0, min(255, int(_gamma(max(0, r)) * 255 + 0.5)))
    g = max(0, min(255, int(_gamma(max(0, g)) * 255 + 0.5)))
    b = max(0, min(255, int(_gamma(max(0, b)) * 255 + 0.5)))
    return (r, g, b)


def lab_to_rgb(
    l_val: float, a_val: float, b_val: float
) -> Tuple[int, int, int]:
    """Convert CIE L*a*b* directly to RGB."""
    x, y, z = lab_to_xyz(l_val, a_val, b_val)
    return xyz_to_rgb(x, y, z)


def convert_color_space(
    image: Image.Image,
    source_cs: ColorSpaceType,
    target_cs: ColorSpaceType = ColorSpaceType.RGB,
    icc_profile: Optional[bytes] = None,
) -> Image.Image:
    """Convert an image between color spaces.

    Uses embedded ICC profiles when available, falls back to
    approximate conversion formulas.
    """
    if source_cs == target_cs:
        return image

    if icc_profile and hasattr(Image, "CmsImagePlugin"):
        try:
            from PIL import ImageCms
            input_profile = ImageCms.createProfile("sRGB")
            output_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_profile))
            return ImageCms.profileToProfile(image, input_profile, output_profile)
        except Exception as e:
            logger.debug("ICC conversion failed, using fallback: %s", e)

    if source_cs == ColorSpaceType.CMYK and target_cs == ColorSpaceType.RGB:
        return cmyk_to_rgb(image)
    if source_cs == ColorSpaceType.GRAYSCALE and target_cs == ColorSpaceType.RGB:
        return image.convert("RGB")
    if source_cs == ColorSpaceType.LAB and target_cs == ColorSpaceType.RGB:
        return _convert_lab_image_to_rgb(image)
    if source_cs == ColorSpaceType.RGB and target_cs == ColorSpaceType.CMYK:
        return image.convert("CMYK")

    logger.warning(
        "Unsupported color space conversion: %s -> %s", source_cs, target_cs
    )
    return image.convert("RGB")


def _convert_lab_image_to_rgb(image: Image.Image) -> Image.Image:
    """Convert a CIE L*a*b* image to RGB pixel by pixel."""
    if image.mode == "L":
        return image.convert("RGB")

    pixels = list(image.getdata())
    width, height = image.size
    rgb_pixels: List[Tuple[int, int, int]] = []

    for pixel in pixels:
        if isinstance(pixel, tuple) and len(pixel) >= 3:
            l_val, a_val, b_val = pixel[0], pixel[1], pixel[2]
            l_scale = l_val * 100.0 / 255.0 if l_val > 1 else l_val * 100.0
            a_shifted = a_val - 128.0 if a_val > 1 else a_val
            b_shifted = b_val - 128.0 if b_val > 1 else b_val
            rgb_pixels.append(lab_to_rgb(l_scale, a_shifted, b_shifted))
        else:
            v = pixel if isinstance(pixel, int) else 0
            rgb_pixels.append(gray_to_rgb(v))

    result = Image.new("RGB", (width, height))
    result.putdata(rgb_pixels)
    return result


# --- Downsampling and Thumbnails ---

def downsample_image(
    image: Image.Image,
    target_dpi: float,
    source_dpi: float = 72.0,
    resample: int = Image.LANCZOS,
) -> Image.Image:
    """Downsample an image from source_dpi to target_dpi.

    Preserves aspect ratio and avoids upscaling.
    """
    if target_dpi >= source_dpi:
        return image

    scale = target_dpi / source_dpi
    new_width = max(1, int(image.width * scale))
    new_height = max(1, int(image.height * scale))

    if new_width >= image.width and new_height >= image.height:
        return image

    return image.resize((new_width, new_height), resample)


def generate_thumbnail(
    image: Image.Image,
    max_width: int = 160,
    max_height: int = 160,
    maintain_aspect: bool = True,
    quality: int = 85,
) -> Image.Image:
    """Generate a thumbnail of the image fitting within the given bounds.

    Uses high-quality resampling and optionally sharpens after resize.
    """
    if maintain_aspect:
        thumb = image.copy()
        thumb.thumbnail((max_width, max_height), Image.LANCZOS)
        return thumb
    return image.resize((max_width, max_height), Image.LANCZOS)


def downsample_for_display(
    image: Image.Image,
    max_dimension: int = 2048,
) -> Image.Image:
    """Downsample large images for efficient on-screen display."""
    w, h = image.size
    if w <= max_dimension and h <= max_dimension:
        return image
    scale = max_dimension / max(w, h)
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    return image.resize((new_w, new_h), Image.LANCZOS)


# --- Alpha Channel ---

def has_alpha_channel(image: Image.Image) -> bool:
    """Check if the image has meaningful alpha transparency."""
    if image.mode in ("RGBA", "LA", "PA"):
        try:
            alpha = image.split()[-1]
            extrema = alpha.getextrema()
            return extrema[0] < 255
        except Exception:
            return True
    if image.mode == "P" and "transparency" in image.info:
        return True
    return False


def extract_alpha(image: Image.Image) -> Optional[Image.Image]:
    """Extract the alpha channel as a grayscale image, if present."""
    if image.mode in ("RGBA", "LA"):
        return image.split()[-1]
    if image.mode == "PA":
        return image.split()[-1]
    if image.mode == "P" and "transparency" in image.info:
        return image.convert("RGBA").split()[-1]
    return None


def flatten_alpha(
    image: Image.Image,
    background: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Flatten alpha channel onto a solid background color."""
    if image.mode not in ("RGBA", "LA", "PA"):
        return image.convert("RGB")

    bg = Image.new("RGB", image.size, background)
    if image.mode == "RGBA":
        bg.paste(image, mask=image.split()[3])
    elif image.mode == "LA":
        rgba = image.convert("RGBA")
        bg.paste(rgba, mask=rgba.split()[3])
    else:
        bg.paste(image.convert("RGB"))
    return bg


def premultiply_alpha(image: Image.Image) -> Image.Image:
    """Premultiply RGB channels by the alpha channel."""
    if image.mode != "RGBA":
        return image

    r, g, b, a = image.split()
    r = r.point(lambda x, a_val=0: x * a_val // 255)
    g = g.point(lambda x, a_val=0: x * a_val // 255)
    b = b.point(lambda x, a_val=0: x * a_val // 255)
    return Image.merge("RGBA", (r, g, b, a))


# --- JPEG 2000 Support ---

def decode_jpx(data: bytes) -> Optional[Image.Image]:
    """Decode JPEG 2000 image data.

    Uses Pillow with openjpg support when available, or falls back to
    treating it as raw RGB if the codec is not compiled in.
    """
    try:
        img = Image.open(io.BytesIO(data))
        return img.copy()
    except Exception as e:
        logger.warning("JPX decode failed: %s", e)
        return None


# --- JBIG2 Support ---

def decode_jbig2(data: bytes, globals_data: Optional[bytes] = None) -> Optional[Image.Image]:
    """Decode JBIG2 image data.

    JBIG2 is typically used for bi-level (1-bit) images in PDFs.
    Falls back to raw bitmap interpretation.
    """
    try:
        img = Image.open(io.BytesIO(data))
        return img.copy()
    except Exception:
        pass

    if len(data) < 8:
        return None

    try:
        width = struct.unpack(">I", data[0:4])[0]
        height = struct.unpack(">I", data[4:8])[0]
        if width > 0 and height > 0 and width * height // 8 + 8 <= len(data):
            bitmap_data = data[8: 8 + (width * height + 7) // 8]
            img = Image.frombytes("1", (width, height), bitmap_data)
            return img
    except Exception as e:
        logger.debug("JBIG2 raw decode failed: %s", e)

    return None


# --- CCITT Support ---

def decode_ccitt(data: bytes, width: int, height: int) -> Optional[Image.Image]:
    """Decode CCITT fax compressed data."""
    try:
        img = Image.open(io.BytesIO(data))
        return img.copy()
    except Exception:
        pass

    if len(data) < 2 or width <= 0 or height <= 0:
        return None

    try:
        row_bytes = (width + 7) // 8
        expected = row_bytes * height
        if len(data) >= expected:
            img = Image.frombytes("1", (width, height), data[:expected])
            return img
    except Exception as e:
        logger.debug("CCITT raw decode failed: %s", e)

    return None


# --- Main Loader ---

class ImageLoader:
    """Loads and decodes images from PDF streams with format detection,
    color space conversion, and caching."""

    def __init__(self, default_dpi: float = 72.0):
        self._default_dpi = default_dpi
        self._cache: Dict[int, DecodedImage] = {}

    def load_from_bytes(
        self,
        data: bytes,
        color_space: Optional[str] = None,
        convert_to_rgb: bool = True,
    ) -> DecodedImage:
        """Load an image from raw bytes with automatic format detection."""
        fmt = detect_image_format(data)
        metadata = self._build_metadata(data, fmt, color_space)
        image = self._decode_bytes(data, fmt)

        if image is None:
            image = Image.new("RGB", (1, 1), (0, 0, 0))
            metadata.format = ImageFormat.UNKNOWN

        image = self._ensure_compatible_mode(image, metadata)

        if convert_to_rgb and image.mode != "RGB":
            cs_type = _classify_color_space(color_space or "")
            image = convert_color_space(image, cs_type, ColorSpaceType.RGB, metadata.icc_profile)

        return DecodedImage(
            image=image,
            metadata=metadata,
            original_bytes=data,
        )

    def load_from_pdf_image(
        self,
        xref: int,
        doc: Any,
        convert_to_rgb: bool = True,
    ) -> DecodedImage:
        """Load an image from a PyMuPDF document by cross-reference number."""
        if xref in self._cache:
            return self._cache[xref]

        try:
            page = doc[0] if len(doc) > 0 else None
            if page is None:
                raise ValueError("Document has no pages")

            base_image = doc.extract_image(xref)
            if not base_image:
                raise ValueError(f"Could not extract image xref={xref}")

            data = base_image.get("image", b"")
            if not data:
                raise ValueError("Empty image data")

            color_space = base_image.get("colorspace", "")
            ext = base_image.get("ext", "")
            width = base_image.get("width", 0)
            height = base_image.get("height", 0)

            fmt = self._extension_to_format(ext)
            metadata = ImageMetadata(
                format=fmt,
                width=width,
                height=height,
                color_space_name=color_space,
                color_space=_classify_color_space(color_space),
                bits_per_component=base_image.get("bpc", 8),
            )

            image = self._decode_bytes(data, fmt)
            if image is None:
                raise ValueError(f"Failed to decode {fmt.name} image")

            image = self._ensure_compatible_mode(image, metadata)

            if convert_to_rgb and image.mode != "RGB":
                image = convert_color_space(
                    image, metadata.color_space, ColorSpaceType.RGB
                )

            result = DecodedImage(
                image=image,
                metadata=metadata,
                original_bytes=data,
            )
            self._cache[xref] = result
            return result

        except Exception as e:
            logger.error("Failed to load PDF image xref=%d: %s", xref, e)
            fallback = Image.new("RGB", (64, 64), (200, 200, 200))
            return DecodedImage(
                image=fallback,
                metadata=ImageMetadata(format=ImageFormat.UNKNOWN),
            )

    def generate_thumbnail_from_pdf(
        self,
        xref: int,
        doc: Any,
        max_size: int = 160,
    ) -> Image.Image:
        """Generate a thumbnail for a PDF image."""
        decoded = self.load_from_pdf_image(xref, doc, convert_to_rgb=True)
        return generate_thumbnail(decoded.image, max_size, max_size)

    def clear_cache(self) -> None:
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        return len(self._cache)

    def _decode_bytes(self, data: bytes, fmt: ImageFormat) -> Optional[Image.Image]:
        if fmt == ImageFormat.UNKNOWN:
            return None

        try:
            if fmt == ImageFormat.JPEG:
                return Image.open(io.BytesIO(data)).copy()
            if fmt == ImageFormat.PNG:
                return Image.open(io.BytesIO(data)).copy()
            if fmt == ImageFormat.TIFF:
                return Image.open(io.BytesIO(data)).copy()
            if fmt == ImageFormat.BMP:
                return Image.open(io.BytesIO(data)).copy()
            if fmt == ImageFormat.GIF:
                return Image.open(io.BytesIO(data)).copy()
            if fmt == ImageFormat.JPX:
                return decode_jpx(data)
            if fmt == ImageFormat.JBIG2:
                return decode_jbig2(data)
            if fmt == ImageFormat.CCITT:
                return decode_ccitt(data, 100, 100)
            return Image.open(io.BytesIO(data)).copy()
        except Exception as e:
            logger.debug("Image decode error (%s): %s", fmt.name, e)
            return None

    def _build_metadata(
        self, data: bytes, fmt: ImageFormat, color_space: Optional[str]
    ) -> ImageMetadata:
        metadata = ImageMetadata(format=fmt, color_space_name=color_space or "")
        metadata.color_space = _classify_color_space(color_space or "")

        try:
            img = Image.open(io.BytesIO(data))
            metadata.width, metadata.height = img.size
            metadata.bits_per_component = _get_bits_per_component(img)
            metadata.has_alpha = has_alpha_channel(img)
            if hasattr(img, "info"):
                dpi = img.info.get("dpi")
                if dpi:
                    metadata.dpi = (float(dpi[0]), float(dpi[1]))
                icc = img.info.get("icc_profile")
                if icc:
                    metadata.icc_profile = icc
        except Exception:
            pass

        if fmt in (ImageFormat.JPEG, ImageFormat.TIFF):
            try:
                metadata.exif_data = extract_exif(data)
            except Exception:
                pass

        return metadata

    @staticmethod
    def _ensure_compatible_mode(
        image: Image.Image, metadata: ImageMetadata
    ) -> Image.Image:
        if image.mode == "CMYK":
            return image
        if image.mode == "YCbCr":
            return image.convert("RGB")
        if image.mode == "1":
            return image.convert("L")
        if image.mode == "I;16":
            return image.convert("L")
        if image.mode == "I":
            return image.convert("L")
        return image

    @staticmethod
    def _extension_to_format(ext: str) -> ImageFormat:
        ext_map = {
            "jpeg": ImageFormat.JPEG,
            "jpg": ImageFormat.JPEG,
            "png": ImageFormat.PNG,
            "tiff": ImageFormat.TIFF,
            "tif": ImageFormat.TIFF,
            "bmp": ImageFormat.BMP,
            "jpx": ImageFormat.JPX,
            "jp2": ImageFormat.JPX,
            "jbig2": ImageFormat.JBIG2,
            "ccitt": ImageFormat.CCITT,
        }
        return ext_map.get(ext.lower(), ImageFormat.UNKNOWN)


def _classify_color_space(cs_name: str) -> ColorSpaceType:
    name = cs_name.lower().strip()
    if not name:
        return ColorSpaceType.UNKNOWN
    if "gray" in name or "grey" in name or name == "devicegray":
        return ColorSpaceType.GRAYSCALE
    if name == "devicergb" or name == "rgb":
        return ColorSpaceType.RGB
    if name == "devicecmyk" or name == "cmyk":
        return ColorSpaceType.CMYK
    if "lab" in name or name == "lab":
        return ColorSpaceType.LAB
    if "calrgb" in name:
        return ColorSpaceType.CALRGB
    if "icc" in name or "iccbased" in name:
        return ColorSpaceType.ICC_BASED
    if "separation" in name:
        return ColorSpaceType.SEPARATION
    if "devicen" in name or "device-n" in name:
        return ColorSpaceType.DEVICE_N
    if "indexed" in name or "index" in name:
        return ColorSpaceType.INDEXED
    return ColorSpaceType.UNKNOWN


def _get_bits_per_component(image: Image.Image) -> int:
    mode_bits = {
        "1": 1,
        "L": 8,
        "P": 8,
        "RGB": 8,
        "RGBA": 8,
        "CMYK": 8,
        "I": 32,
        "F": 32,
    }
    return mode_bits.get(image.mode, 8)
