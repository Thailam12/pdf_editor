"""Virtual PDF printer: convert any printable document to PDF via virtual printer driver."""

import os
import logging
import tempfile
import platform
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class VirtualPrinterConfig:
    name: str = "PDFMind Virtual Printer"
    output_dir: str = ""
    auto_open: bool = True
    prompt_filename: bool = True
    default_prefix: str = "Printed_"
    compress_output: bool = True
    add_metadata: bool = True
    preserve_bookmarks: bool = True
    page_size_override: str = ""
    always_landscape: bool = False
    apply_watermark: str = ""
    watermarks: list = field(default_factory=list)


@dataclass
class VirtualPrintJob:
    job_id: int = 0
    source_app: str = ""
    document_name: str = ""
    output_path: str = ""
    status: str = "pending"
    pages_printed: int = 0
    file_size: int = 0


class VirtualPDFPrinter:
    """Virtual PDF printer that captures print output and converts to PDF."""

    PAPER_SIZES = {
        "letter": {"width": 612, "height": 792},
        "legal": {"width": 612, "height": 1008},
        "tabloid": {"width": 792, "height": 1224},
        "A4": {"width": 595, "height": 842},
        "A3": {"width": 842, "height": 1191},
        "A5": {"width": 420, "height": 595},
    }

    def __init__(self, config: VirtualPrinterConfig = None):
        self._config = config or VirtualPrinterConfig()
        self._job_counter = 0
        self._completed_jobs: list[VirtualPrintJob] = []
        if not self._config.output_dir:
            self._config.output_dir = tempfile.mkdtemp(prefix="pdfmind_printer_")
        os.makedirs(self._config.output_dir, exist_ok=True)

    def get_config(self) -> VirtualPrinterConfig:
        return self._config

    def update_config(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)

    def get_output_directory(self) -> str:
        return self._config.output_dir

    def set_output_directory(self, path: str):
        self._config.output_dir = path
        os.makedirs(path, exist_ok=True)

    def generate_output_path(self, source_name: str = "document") -> str:
        import time
        base_name = os.path.splitext(source_name)[0]
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in base_name)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{self._config.default_prefix}{safe_name}_{timestamp}.pdf"
        return os.path.join(self._config.output_dir, filename)

    def start_print_job(self, source_app: str = "", document_name: str = "") -> VirtualPrintJob:
        self._job_counter += 1
        output_path = self.generate_output_path(document_name or f"job_{self._job_counter}")
        job = VirtualPrintJob(
            job_id=self._job_counter,
            source_app=source_app,
            document_name=document_name,
            output_path=output_path,
            status="printing",
        )
        return job

    def complete_print_job(self, job: VirtualPrintJob, pdf_data: bytes) -> VirtualPrintJob:
        with open(job.output_path, "wb") as f:
            f.write(pdf_data)
        job.file_size = len(pdf_data)
        job.status = "completed"
        self._completed_jobs.append(job)
        if self._config.auto_open:
            logger.info(f"Auto-opening: {job.output_path}")
        logger.info(f"Print job {job.job_id} completed: {job.output_path} ({job.file_size} bytes)")
        return job

    def convert_text_to_pdf(self, text: str, output_path: str = None,
                             font_size: int = 12, page_size: str = "letter") -> str:
        from reportlab.lib.pagesizes import letter, A4, legal
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle

        size_map = {"letter": letter, "A4": A4, "legal": legal}
        page = size_map.get(page_size, letter)
        if output_path is None:
            output_path = self.generate_output_path("text_output")
        doc = SimpleDocTemplate(output_path, pagesize=page,
                                topMargin=72, bottomMargin=72,
                                leftMargin=72, rightMargin=72)
        styles = getSampleStyleSheet()
        style = ParagraphStyle("CustomBody", parent=styles["Normal"], fontSize=font_size, leading=font_size * 1.5)
        paragraphs = [Paragraph(line, style) for line in text.split("\n") if line.strip()]
        doc.build(paragraphs)
        logger.info(f"Text to PDF: {output_path}")
        return output_path

    def merge_print_outputs(self, outputs: list[str], final_path: str = None) -> str:
        if not outputs:
            raise ValueError("No outputs to merge")
        try:
            from pypdf import PdfWriter, PdfReader
            writer = PdfWriter()
            for path in outputs:
                if os.path.exists(path):
                    reader = PdfReader(path)
                    for page in reader.pages:
                        writer.add_page(page)
            if final_path is None:
                final_path = self.generate_output_path("merged_output")
            with open(final_path, "wb") as f:
                writer.write(f)
            logger.info(f"Merged {len(outputs)} outputs to: {final_path}")
            return final_path
        except ImportError:
            logger.error("pypdf not available for merging")
            return outputs[0] if outputs else ""

    def get_printer_driver_info(self) -> dict:
        return {
            "name": self._config.name,
            "output_dir": self._config.output_dir,
            "auto_open": self._config.auto_open,
            "compress": self._config.compress_output,
            "metadata": self._config.add_metadata,
            "supported_paper_sizes": list(self.PAPER_SIZES.keys()),
            "platform": platform.system(),
            "driver_type": "virtual_pdf",
            "version": "1.0.0",
        }

    def get_completed_jobs(self) -> list[VirtualPrintJob]:
        return list(self._completed_jobs)

    def clear_completed_jobs(self):
        self._completed_jobs.clear()

    def install_printer_driver(self) -> bool:
        logger.info("Virtual PDF printer driver installation initiated")
        info = self.get_printer_driver_info()
        config_path = os.path.join(self._config.output_dir, "printer_config.json")
        import json
        with open(config_path, "w") as f:
            json.dump(info, f, indent=2)
        logger.info(f"Printer config written to: {config_path}")
        return True

    def get_spool_info(self) -> dict:
        return {
            "active_jobs": 0,
            "queued_jobs": 0,
            "completed_jobs": len(self._completed_jobs),
            "total_output_size": sum(j.file_size for j in self._completed_jobs),
            "output_dir": self._config.output_dir,
        }
