"""DjVu import: read DjVu documents and convert to PDF."""

import os
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DjVuPageInfo:
    index: int = 0
    width: int = 0
    height: int = 0
    has_text: bool = False
    text_content: str = ""
    dpi: int = 300


@dataclass
class DjVuDocumentInfo:
    file_path: str = ""
    page_count: int = 0
    title: str = ""
    author: str = ""
    pages: list[DjVuPageInfo] = field(default_factory=list)
    file_size: int = 0
    metadata: dict = field(default_factory=dict)


class DjVuImporter:
    """Import DjVu documents using DjVuLibr's djvulibre tools for PDF conversion."""

    DJVUTXT = "djvutxt"
    DJVUSED = "djvused"
    DDJVU = "ddjvu"

    def __init__(self, djvulibre_path: str = ""):
        self._djvulibre_path = djvulibre_path
        self._tools_available = self._check_tools()

    def _check_tools(self) -> bool:
        try:
            result = subprocess.run(
                [self.DDJVU, "-v"], capture_output=True, text=True, timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def is_available(self) -> bool:
        return self._tools_available

    def get_info(self, djvu_path: str) -> DjVuDocumentInfo:
        info = DjVuDocumentInfo(file_path=djvu_path)
        if os.path.exists(djvu_path):
            info.file_size = os.path.getsize(djvu_path)
        if not self._tools_available:
            logger.warning("DjVuLibr tools not available; returning basic info")
            return info
        try:
            text = self._run_djvutxt(djvu_path)
            info.page_count = text.count("\f") + 1 if text else 0
        except Exception as e:
            logger.error(f"Failed to get DjVu info: {e}")
        return info

    def extract_text(self, djvu_path: str) -> str:
        if not self._tools_available:
            raise RuntimeError("DjVuLibr tools not available")
        return self._run_djvutxt(djvu_path)

    def extract_page_text(self, djvu_path: str, page: int) -> str:
        if not self._tools_available:
            raise RuntimeError("DjVuLibr tools not available")
        try:
            result = subprocess.run(
                [self.DJVUTXT, "-page", str(page), djvu_path],
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout
        except Exception as e:
            logger.error(f"Failed to extract page text: {e}")
            return ""

    def extract_all_text(self, djvu_path: str) -> list[str]:
        full_text = self.extract_text(djvu_path)
        return full_text.split("\f") if full_text else []

    def convert_to_pdf(self, djvu_path: str, output_path: str, dpi: int = 300) -> str:
        if not self._tools_available:
            raise RuntimeError("DjVuLibr tools not available for conversion")
        try:
            cmd = [self.DDJVU, "-format", "pdf", "-dpi", str(dpi), djvu_path, output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"ddjvu failed: {result.stderr}")
            logger.info(f"DjVu to PDF: {djvu_path} -> {output_path}")
            return output_path
        except subprocess.TimeoutExpired:
            raise RuntimeError("Conversion timed out")

    def convert_page_to_image(self, djvu_path: str, page: int, output_path: str,
                               dpi: int = 300, format: str = "png") -> str:
        if not self._tools_available:
            raise RuntimeError("DjVuLibr tools not available")
        cmd = [self.DDJVU, "-format", format, "-dpi", str(dpi),
               "-page", str(page), djvu_path, output_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ddjvu page conversion failed: {result.stderr}")
        return output_path

    def convert_to_tiff(self, djvu_path: str, output_path: str, dpi: int = 300) -> str:
        return self.convert_to_pdf(djvu_path, output_path.replace(".tiff", ".pdf"), dpi)

    def get_metadata(self, djvu_path: str) -> dict:
        metadata = {}
        if not self._tools_available:
            return metadata
        try:
            cmd = [self.DJVUSED, djvu_path, "-e", "print-meta"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if ":" in line:
                        key, _, value = line.partition(":")
                        metadata[key.strip()] = value.strip()
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
        return metadata

    def get_page_info(self, djvu_path: str, page: int) -> DjVuPageInfo:
        info = DjVuPageInfo(index=page)
        if not self._tools_available:
            return info
        try:
            text = self.extract_page_text(djvu_path, page)
            info.has_text = bool(text.strip())
            info.text_content = text
        except Exception:
            pass
        return info

    def batch_convert(self, djvu_files: list[str], output_dir: str, dpi: int = 300) -> list[str]:
        os.makedirs(output_dir, exist_ok=True)
        results = []
        for djvu_path in djvu_files:
            try:
                base = os.path.splitext(os.path.basename(djvu_path))[0]
                output_path = os.path.join(output_dir, f"{base}.pdf")
                self.convert_to_pdf(djvu_path, output_path, dpi)
                results.append(output_path)
            except Exception as e:
                logger.error(f"Failed to convert {djvu_path}: {e}")
        return results

    def _run_djvutxt(self, djvu_path: str) -> str:
        result = subprocess.run(
            [self.DJVUTXT, djvu_path], capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(f"djvutxt failed: {result.stderr}")
        return result.stdout

    def get_capabilities(self) -> dict:
        return {
            "import": True,
            "export_pdf": self._tools_available,
            "export_images": self._tools_available,
            "text_extraction": self._tools_available,
            "metadata": self._tools_available,
            "batch_conversion": self._tools_available,
            "tools_available": self._tools_available,
        }
