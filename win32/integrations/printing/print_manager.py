"""Advanced print management: printer discovery, job management, preview, and print settings."""

import os
import logging
import platform
import tempfile
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import win32print
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import subprocess
    HAS_SUBPROCESS = True
except ImportError:
    HAS_SUBPROCESS = False


@dataclass
class PrintSettings:
    printer_name: str = "default"
    copies: int = 1
    duplex: str = "none"
    color_mode: str = "color"
    paper_size: str = "A4"
    orientation: str = "portrait"
    page_ranges: list[str] = field(default_factory=list)
    reverse_order: bool = False
    fit_to_page: bool = True
    scale_factor: float = 100.0
    margin_top: float = 0.5
    margin_bottom: float = 0.5
    margin_left: float = 0.5
    margin_right: float = 0.5
    collate: bool = True
    print_quality: str = "normal"
    draft_mode: bool = False
    header_text: str = ""
    footer_text: str = ""
    print_to_file: bool = False
    output_path: str = ""


@dataclass
class PrinterInfo:
    name: str = ""
    is_default: bool = False
    is_shared: bool = False
    port: str = ""
    driver: str = ""
    status: str = "idle"
    paper_sizes: list[str] = field(default_factory=list)
    supports_duplex: bool = False
    supports_color: bool = False
    dpi_x: int = 300
    dpi_y: int = 300


@dataclass
class PrintJob:
    job_id: int = 0
    document_name: str = ""
    printer_name: str = ""
    status: str = "pending"
    pages_printed: int = 0
    total_pages: int = 0
    submitted_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    error: str = ""


class PrintManager:
    """Advanced print management with printer discovery, job tracking, and settings."""

    PAPER_SIZES = {
        "letter": (8.5, 11), "legal": (8.5, 14), "tabloid": (11, 17),
        "A4": (8.27, 11.69), "A3": (11.69, 16.54), "A5": (5.83, 8.27),
        "B5": (6.93, 9.84), "Executive": (7.25, 10.5),
        "Envelope #10": (4.125, 9.5), "Envelope DL": (4.33, 8.66),
    }

    def __init__(self):
        self._active_jobs: dict[int, PrintJob] = {}
        self._job_counter = 0

    def list_printers(self) -> list[PrinterInfo]:
        printers = []
        if HAS_WIN32:
            try:
                default = win32print.GetDefaultPrinter()
                flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
                for name in win32print.EnumPrinters(flags):
                    info = PrinterInfo(
                        name=name[2], is_default=(name[2] == default),
                        port=name[3] if len(name) > 3 else "",
                        driver=name[4] if len(name) > 4 else "",
                    )
                    try:
                        handle = win32print.OpenPrinter(name[2])
                        pinfo = win32print.GetPrinter(handle, 2)
                        status = pinfo.get("Status", 0)
                        if status == 0:
                            info.status = "idle"
                        elif status & win32print.PRINTER_STATUS_BUSY:
                            info.status = "busy"
                        elif status & win32print.PRINTER_STATUS_ERROR:
                            info.status = "error"
                        else:
                            info.status = "online"
                        win32print.ClosePrinter(handle)
                    except Exception:
                        pass
                    printers.append(info)
            except Exception as e:
                logger.error(f"Failed to enumerate printers: {e}")
        else:
            printers.append(PrinterInfo(name="Default Printer", is_default=True, status="idle"))
        return printers

    def get_default_printer(self) -> Optional[PrinterInfo]:
        printers = self.list_printers()
        for p in printers:
            if p.is_default:
                return p
        return printers[0] if printers else None

    def get_printer_info(self, name: str) -> Optional[PrinterInfo]:
        for p in self.list_printers():
            if p.name == name:
                return p
        return None

    def validate_settings(self, settings: PrintSettings) -> list[str]:
        warnings = []
        if settings.copies < 1:
            warnings.append("Copies must be at least 1")
        if settings.scale_factor < 10 or settings.scale_factor > 200:
            warnings.append("Scale factor should be between 10% and 200%")
        if settings.orientation not in ("portrait", "landscape"):
            warnings.append(f"Invalid orientation: {settings.orientation}")
        if settings.paper_size not in self.PAPER_SIZES and settings.paper_size not in ["A4", "A3"]:
            warnings.append(f"Unknown paper size: {settings.paper_size}")
        if settings.margin_top < 0 or settings.margin_bottom < 0:
            warnings.append("Margins cannot be negative")
        return warnings

    def apply_settings(self, settings: PrintSettings) -> dict:
        validated = self.validate_settings(settings)
        if validated:
            logger.warning(f"Settings warnings: {validated}")
        config = {
            "printer": settings.printer_name,
            "copies": settings.copies,
            "duplex": settings.duplex,
            "color": settings.color_mode,
            "paper": settings.paper_size,
            "orientation": settings.orientation,
            "ranges": settings.page_ranges,
            "reverse": settings.reverse_order,
            "fit_to_page": settings.fit_to_page,
            "scale": settings.scale_factor,
            "margins": {
                "top": settings.margin_top,
                "bottom": settings.margin_bottom,
                "left": settings.margin_left,
                "right": settings.margin_right,
            },
            "collate": settings.collate,
            "quality": settings.print_quality,
            "draft": settings.draft_mode,
        }
        return config

    def print_pdf(self, pdf_path: str, settings: PrintSettings = None) -> PrintJob:
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        settings = settings or PrintSettings()
        self._job_counter += 1
        job = PrintJob(
            job_id=self._job_counter,
            document_name=os.path.basename(pdf_path),
            printer_name=settings.printer_name,
            status="queued",
            submitted_at=self._timestamp(),
        )
        self._active_jobs[job.job_id] = job
        logger.info(f"Print job {job.job_id} queued: {pdf_path}")
        if settings.print_to_file:
            output = settings.output_path or pdf_path.replace(".pdf", "_printed.pdf")
            job.status = "completed"
            job.completed_at = self._timestamp()
            logger.info(f"Print to file: {output}")
        return job

    def get_job_status(self, job_id: int) -> Optional[PrintJob]:
        return self._active_jobs.get(job_id)

    def cancel_job(self, job_id: int) -> bool:
        job = self._active_jobs.get(job_id)
        if job and job.status in ("queued", "printing"):
            job.status = "cancelled"
            logger.info(f"Print job {job_id} cancelled")
            return True
        return False

    def get_page_count_estimate(self, pdf_path: str, settings: PrintSettings = None) -> int:
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            pages = len(reader.pages)
            if settings and settings.page_ranges:
                count = 0
                for r in settings.page_ranges:
                    if "-" in r:
                        start, end = r.split("-")
                        count += int(end) - int(start) + 1
                    else:
                        count += 1
                return count * (settings.copies or 1)
            return pages * (settings.copies if settings else 1)
        except Exception:
            return 0

    def generate_print_preview_data(self, pdf_path: str, settings: PrintSettings = None) -> dict:
        settings = settings or PrintSettings()
        paper = self.PAPER_SIZES.get(settings.paper_size, (8.5, 11))
        page_w = paper[0] if settings.orientation == "portrait" else paper[1]
        page_h = paper[1] if settings.orientation == "portrait" else paper[0]
        return {
            "document": pdf_path,
            "paper_size": settings.paper_size,
            "page_width_inches": page_w,
            "page_height_inches": page_h,
            "orientation": settings.orientation,
            "margins": {
                "top": settings.margin_top, "bottom": settings.margin_bottom,
                "left": settings.margin_left, "right": settings.margin_right,
            },
            "effective_width": page_w - settings.margin_left - settings.margin_right,
            "effective_height": page_h - settings.margin_top - settings.margin_bottom,
            "scale_factor": settings.scale_factor,
            "copies": settings.copies,
            "estimated_pages": self.get_page_count_estimate(pdf_path, settings),
        }

    def create_default_settings(self, printer_name: str = None) -> PrintSettings:
        settings = PrintSettings()
        if printer_name:
            settings.printer_name = printer_name
        default = self.get_default_printer()
        if default:
            settings.printer_name = default.name
        return settings

    def _timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().isoformat()
