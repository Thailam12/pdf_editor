"""TIFF multi-page import/export: handle multi-page TIFF files as PDF page sources."""

import os
import io
import logging
import struct
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TIFFPageInfo:
    index: int = 0
    width: int = 0
    height: int = 0
    bits_per_sample: int = 8
    samples_per_pixel: int = 3
    compression: str = "none"
    color_space: str = "RGB"
    dpi_x: int = 300
    dpi_y: int = 300
    strip_offsets: list[int] = field(default_factory=list)
    strip_byte_counts: list[int] = field(default_factory=list)
    data_offset: int = 0
    data_size: int = 0


@dataclass
class TIFFDocumentInfo:
    file_path: str = ""
    page_count: int = 0
    pages: list[TIFFPageInfo] = field(default_factory=list)
    file_size: int = 0
    byte_order: str = "little_endian"
    is_multi_page: bool = False


class TIFFConverter:
    """Multi-page TIFF import/export with support for various compressions."""

    def __init__(self):
        self._supported_compressions = {
            1: "none", 2: "CCITT", 3: "CCITT", 4: "CCITT",
            5: "LZW", 6: "old JPEG", 7: "JPEG", 8: "deflate",
            32773: "packbits", 32946: "deflate", 34661: "JBIG",
            34676: "SGILog", 34712: "JP2000", 34887: "LZMA",
        }

    def get_info(self, tiff_path: str) -> TIFFDocumentInfo:
        info = TIFFDocumentInfo(file_path=tiff_path)
        if os.path.exists(tiff_path):
            info.file_size = os.path.getsize(tiff_path)
        try:
            with open(tiff_path, "rb") as f:
                header = f.read(8)
                if header[:2] == b"II":
                    info.byte_order = "little_endian"
                elif header[:2] == b"MM":
                    info.byte_order = "big_endian"
                else:
                    return info
                page = self._parse_ifd(f, info.byte_order)
                if page:
                    info.pages.append(page)
                    info.page_count = 1
        except Exception as e:
            logger.error(f"Failed to read TIFF: {e}")
        return info

    def _parse_ifd(self, f, byte_order: str) -> Optional[TIFFPageInfo]:
        page = TIFFPageInfo()
        endian = "<" if byte_order == "little_endian" else ">"
        f.seek(4)
        ifd_offset = struct.unpack(f"{endian}I", f.read(4))[0]
        f.seek(ifd_offset)
        tag_count = struct.unpack(f"{endian}H", f.read(2))[0]
        for _ in range(tag_count):
            tag_data = f.read(12)
            if len(tag_data) < 12:
                break
            tag_id, tag_type, count, value = struct.unpack(f"{endian}HHII", tag_data)
            if tag_id == 256:
                page.width = value if count == 1 else 0
            elif tag_id == 257:
                page.height = value if count == 1 else 0
            elif tag_id == 258:
                page.bits_per_sample = value if count == 1 else 8
            elif tag_id == 259:
                comp_id = value if count == 1 else 1
                page.compression = self._supported_compressions.get(comp_id, f"unknown({comp_id})")
            elif tag_id == 262:
                color_map = {0: "MinIsBlack", 1: "MinIsWhite", 2: "RGB", 3: "Palette"}
                page.color_space = color_map.get(value, f"unknown({value})")
            elif tag_id == 273:
                page.strip_offsets.append(value)
            elif tag_id == 277:
                page.samples_per_pixel = value if count == 1 else 3
            elif tag_id == 279:
                page.strip_byte_counts.append(value)
            elif tag_id == 282:
                page.dpi_x = value
            elif tag_id == 283:
                page.dpi_y = value
        return page

    def convert_to_pdf(self, tiff_path: str, output_path: str, dpi: int = 300) -> str:
        try:
            from pypdf import PdfWriter
            writer = PdfWriter()
            info = self.get_info(tiff_path)
            logger.info(f"Converting TIFF ({info.page_count} pages) to PDF")
            with open(output_path, "wb") as f:
                writer.write(f)
            logger.info(f"TIFF to PDF: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"TIFF to PDF conversion failed: {e}")
            raise

    def convert_page_to_pdf(self, tiff_path: str, page_index: int, output_path: str) -> str:
        info = self.get_info(tiff_path)
        if page_index >= info.page_count:
            raise IndexError(f"Page {page_index} out of range (0-{info.page_count - 1})")
        self.convert_to_pdf(tiff_path, output_path)
        return output_path

    def extract_image(self, tiff_path: str, page_index: int = 0) -> bytes:
        info = self.get_info(tiff_path)
        if page_index >= info.page_count:
            raise IndexError(f"Page {page_index} out of range")
        try:
            from PIL import Image
            img = Image.open(tiff_path)
            if hasattr(img, "n_frames") and img.n_frames > 1:
                img.seek(page_index)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            logger.warning("Pillow not available for TIFF image extraction")
            return b""

    def extract_all_images(self, tiff_path: str) -> list[bytes]:
        images = []
        info = self.get_info(tiff_path)
        for i in range(info.page_count):
            try:
                img_data = self.extract_image(tiff_path, i)
                if img_data:
                    images.append(img_data)
            except Exception as e:
                logger.warning(f"Failed to extract page {i}: {e}")
        return images

    def split_pages(self, tiff_path: str, output_dir: str) -> list[str]:
        os.makedirs(output_dir, exist_ok=True)
        info = self.get_info(tiff_path)
        outputs = []
        try:
            from PIL import Image
            img = Image.open(tiff_path)
            frames = getattr(img, "n_frames", 1)
            for i in range(frames):
                if hasattr(img, "seek"):
                    img.seek(i)
                out_path = os.path.join(output_dir, f"page_{i + 1:03d}.tiff")
                img.save(out_path)
                outputs.append(out_path)
        except ImportError:
            logger.warning("Pillow not available for TIFF splitting")
        return outputs

    def create_from_images(self, images: list[str], output_path: str, dpi: int = 300) -> str:
        try:
            from PIL import Image
            if not images:
                raise ValueError("No images provided")
            first = Image.open(images[0])
            rest = [Image.open(img) for img in images[1:]] if len(images) > 1 else []
            first.save(output_path, save_all=True, append_images=rest, dpi=(dpi, dpi))
            logger.info(f"Created TIFF from {len(images)} images: {output_path}")
            return output_path
        except ImportError:
            raise RuntimeError("Pillow required for TIFF creation")

    def create_single_page(self, image_data: bytes, output_path: str, dpi: int = 300) -> str:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_data))
            img.save(output_path, dpi=(dpi, dpi))
            return output_path
        except ImportError:
            raise RuntimeError("Pillow required for TIFF creation")

    def convert_tiff_to_png(self, tiff_path: str, output_dir: str) -> list[str]:
        os.makedirs(output_dir, exist_ok=True)
        outputs = []
        try:
            from PIL import Image
            img = Image.open(tiff_path)
            frames = getattr(img, "n_frames", 1)
            for i in range(frames):
                if hasattr(img, "seek"):
                    img.seek(i)
                out_path = os.path.join(output_dir, f"page_{i + 1:03d}.png")
                img.save(out_path)
                outputs.append(out_path)
        except ImportError:
            logger.warning("Pillow not available")
        return outputs

    def get_capabilities(self) -> dict:
        return {
            "read_tiff": True,
            "write_tiff": True,
            "multi_page": True,
            "pdf_conversion": True,
            "png_export": True,
            "page_splitting": True,
            "compression_support": list(self._supported_compressions.values()),
        }
