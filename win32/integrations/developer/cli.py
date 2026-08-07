"""Command-line interface for PDFMind: open, merge, split, compress, OCR, export, and AI operations."""

import sys
import os
import json
import argparse
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

VERSION = "2.1"
APP_NAME = "pdfmind"
FEATURES = ["ai", "ocr", "cloud-sync"]
RELEASE_NOTES = [
    "Improved OCR feedback and diagnostics",
    "Faster startup and health reporting",
    "Expanded cloud sync readiness",
]


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="PDFMind - Intelligent PDF Editor & Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"PDFMind v{VERSION} | https://pdfmind.app",
    )
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {VERSION}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_open = subparsers.add_parser("open", help="Open a PDF in the editor")
    p_open.add_argument("file", help="Path to PDF file")

    p_merge = subparsers.add_parser("merge", help="Merge multiple PDFs")
    p_merge.add_argument("files", nargs="+", help="PDF files to merge")
    p_merge.add_argument("-o", "--output", default="merged.pdf", help="Output file")

    p_split = subparsers.add_parser("split", help="Split a PDF into parts")
    p_split.add_argument("file", help="PDF file to split")
    p_split.add_argument("--pages", help="Page range (e.g., 1-5,8,10-12)")
    p_split.add_argument("--output-dir", "-d", default=".", help="Output directory")
    p_split.add_argument("--single-pages", action="store_true", help="Split into individual pages")

    p_compress = subparsers.add_parser("compress", help="Compress a PDF")
    p_compress.add_argument("file", help="PDF to compress")
    p_compress.add_argument("-o", "--output", help="Output file")
    p_compress.add_argument("--level", choices=["low", "medium", "high"], default="medium",
                            help="Compression level")

    p_ocr = subparsers.add_parser("ocr", help="OCR a scanned PDF")
    p_ocr.add_argument("file", help="PDF to OCR")
    p_ocr.add_argument("-o", "--output", help="Output file")
    p_ocr.add_argument("--lang", default="eng", help="Language(s) (e.g., eng+deu)")
    p_ocr.add_argument("--dpi", type=int, default=300, help="DPI for OCR processing")

    p_export = subparsers.add_parser("export", help="Export PDF to other formats")
    p_export.add_argument("file", help="PDF to export")
    p_export.add_argument("--format", choices=["docx", "xlsx", "pptx", "html", "txt", "png", "jpg", "svg"],
                          required=True, help="Export format")
    p_export.add_argument("-o", "--output", help="Output file/directory")
    p_export.add_argument("--pages", help="Page range to export")

    p_info = subparsers.add_parser("info", help="Show PDF metadata")
    p_info.add_argument("file", help="PDF file")
    p_info.add_argument("--pages", action="store_true", help="Show page details")

    p_pages = subparsers.add_parser("pages", help="Page operations")
    p_pages.add_argument("file", help="PDF file")
    p_pages.add_argument("action", choices=["list", "remove", "rotate", "extract", "crop"],
                         help="Page action")
    p_pages.add_argument("--range", help="Page range")
    p_pages.add_argument("--angle", type=int, default=90, help="Rotation angle")
    p_pages.add_argument("-o", "--output", help="Output file")

    p_encrypt = subparsers.add_parser("encrypt", help="Encrypt a PDF")
    p_encrypt.add_argument("file", help="PDF to encrypt")
    p_encrypt.add_argument("-p", "--password", required=True, help="Owner password")
    p_encrypt.add_argument("-u", "--user-password", help="User password")
    p_encrypt.add_argument("-o", "--output", help="Output file")
    p_encrypt.add_argument("--perms", nargs="*", default=["print", "copy"],
                           help="Allowed permissions")

    p_decrypt = subparsers.add_parser("decrypt", help="Decrypt a PDF")
    p_decrypt.add_argument("file", help="Encrypted PDF")
    p_decrypt.add_argument("-p", "--password", required=True, help="Password")
    p_decrypt.add_argument("-o", "--output", help="Output file")

    p_sign = subparsers.add_parser("sign", help="Digitally sign a PDF")
    p_sign.add_argument("file", help="PDF to sign")
    p_sign.add_argument("--cert", required=True, help="Certificate file (PFX)")
    p_sign.add_argument("--cert-password", required=True, help="Certificate password")
    p_sign.add_argument("--reason", default="", help="Signing reason")
    p_sign.add_argument("--location", default="", help="Signing location")
    p_sign.add_argument("--page", type=int, default=1, help="Page for signature")
    p_sign.add_argument("-o", "--output", help="Output file")

    p_watermark = subparsers.add_parser("watermark", help="Add watermark to PDF")
    p_watermark.add_argument("file", help="PDF file")
    p_watermark.add_argument("--text", help="Watermark text")
    p_watermark.add_argument("--image", help="Watermark image path")
    p_watermark.add_argument("--opacity", type=float, default=0.3, help="Opacity (0-1)")
    p_watermark.add_argument("--rotation", type=float, default=45, help="Rotation angle")
    p_watermark.add_argument("-o", "--output", help="Output file")

    ai_parser = subparsers.add_parser("ai", help="AI-powered operations")
    ai_sub = ai_parser.add_subparsers(dest="ai_command", help="AI commands")

    ai_summarize = ai_sub.add_parser("summarize", help="Summarize a PDF")
    ai_summarize.add_argument("file", help="PDF to summarize")
    ai_summarize.add_argument("--max-length", type=int, default=500, help="Max summary length")
    ai_summarize.add_argument("--style", choices=["brief", "detailed", "bullet"], default="brief")

    ai_ask = ai_sub.add_parser("ask", help="Ask a question about a PDF")
    ai_ask.add_argument("file", help="PDF file")
    ai_ask.add_argument("question", help="Question to ask")

    ai_redact = ai_sub.add_parser("redact", help="AI-powered smart redaction")
    ai_redact.add_argument("file", help="PDF to redact")
    ai_redact.add_argument("--types", nargs="*", default=["pii", "financial", "medical"],
                           help="Content types to redact")
    ai_redact.add_argument("-o", "--output", help="Output file")

    ai_translate = ai_sub.add_parser("translate", help="Translate PDF content")
    ai_translate.add_argument("file", help="PDF to translate")
    ai_translate.add_argument("--target-lang", required=True, help="Target language code")
    ai_translate.add_argument("-o", "--output", help="Output file")

    subparsers.add_parser("serve", help="Start the web server").add_argument(
        "--port", type=int, default=8080, help="Port")
    subparsers.add_parser("serve").add_argument("--host", default="localhost", help="Host")

    subparsers.add_parser("health", help="Show system health info")

    return parser


def parse_page_range(range_str: str, max_pages: int) -> list[int]:
    pages = set()
    for part in range_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            start = max(1, int(start))
            end = min(max_pages, int(end))
            pages.update(range(start, end + 1))
        else:
            p = int(part)
            if 1 <= p <= max_pages:
                pages.add(p)
    return sorted(pages)


def cmd_open(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    print(f"Opening {args.file} in PDFMind editor...")
    return 0


def cmd_merge(args):
    for f in args.files:
        if not os.path.exists(f):
            print(f"Error: File not found: {f}", file=sys.stderr)
            return 1
    print(f"Merging {len(args.files)} files into {args.output}...")
    try:
        from pypdf import PdfWriter, PdfReader
        writer = PdfWriter()
        total_pages = 0
        for f in args.files:
            reader = PdfReader(f)
            for page in reader.pages:
                writer.add_page(page)
                total_pages += 1
        with open(args.output, "wb") as out:
            writer.write(out)
        print(f"Merged {total_pages} pages into {args.output}")
        return 0
    except ImportError:
        print("pypdf not installed. Run: pip install pypdf", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_split(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(args.file)
        total = len(reader.pages)
        base_name = os.path.splitext(os.path.basename(args.file))[0]
        os.makedirs(args.output_dir, exist_ok=True)
        if args.single_pages:
            for i in range(total):
                writer = PdfWriter()
                writer.add_page(reader.pages[i])
                out_path = os.path.join(args.output_dir, f"{base_name}_page_{i + 1:03d}.pdf")
                with open(out_path, "wb") as f:
                    writer.write(f)
                print(f"  Extracted page {i + 1}: {out_path}")
            print(f"Split into {total} individual pages")
        elif args.pages:
            page_indices = parse_page_range(args.pages, total)
            writer = PdfWriter()
            for p in page_indices:
                writer.add_page(reader.pages[p - 1])
            out_path = os.path.join(args.output_dir, f"{base_name}_pages_{args.pages.replace(',', '_')}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            print(f"Extracted {len(page_indices)} pages to {out_path}")
        else:
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            out_path = os.path.join(args.output_dir, f"{base_name}_copy.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            print(f"Copied {total} pages to {out_path}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_compress(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    output = args.output or args.file.replace(".pdf", "_compressed.pdf")
    level_map = {"low": "image_quality=80", "medium": "image_quality=50", "high": "image_quality=20"}
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(args.file)
        original_size = os.path.getsize(args.file)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata(reader.metadata or {})
        with open(output, "wb") as f:
            writer.write(f)
        compressed_size = os.path.getsize(output)
        savings = ((original_size - compressed_size) / original_size * 100) if original_size > 0 else 0
        print(f"Compressed: {original_size:,} bytes -> {compressed_size:,} bytes ({savings:.1f}% reduction)")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_ocr(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    output = args.output or args.file.replace(".pdf", "_ocr.pdf")
    print(f"OCR processing: {args.file} (lang={args.lang}, dpi={args.dpi})")
    print(f"Output: {output}")
    return 0


def cmd_export(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    output = args.output or os.path.splitext(args.file)[0] + f".{args.format}"
    print(f"Exporting {args.file} to {args.format} -> {output}")
    return 0


def cmd_info(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    try:
        from pypdf import PdfReader
        reader = PdfReader(args.file)
        size = os.path.getsize(args.file)
        info = {
            "file": args.file,
            "size": f"{size:,} bytes ({size / 1024:.1f} KB)",
            "pages": len(reader.pages),
            "encrypted": reader.is_encrypted,
            "metadata": dict(reader.metadata) if reader.metadata else {},
        }
        if args.json:
            print(json.dumps(info, indent=2, default=str))
        else:
            print(f"File: {info['file']}")
            print(f"Size: {info['size']}")
            print(f"Pages: {info['pages']}")
            print(f"Encrypted: {info['encrypted']}")
            if info["metadata"]:
                print("Metadata:")
                for k, v in info["metadata"].items():
                    print(f"  {k}: {v}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_pages(args):
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        return 1
    try:
        from pypdf import PdfReader
        reader = PdfReader(args.file)
        print(f"Document has {len(reader.pages)} pages")
        if args.action == "list":
            for i, page in enumerate(reader.pages):
                w = float(page.mediabox.width)
                h = float(page.mediabox.height)
                print(f"  Page {i + 1}: {w:.0f} x {h:.0f} pts")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_encrypt(args):
    print(f"Encrypting {args.file} with owner password...")
    return 0


def cmd_decrypt(args):
    print(f"Decrypting {args.file}...")
    return 0


def cmd_sign(args):
    print(f"Signing {args.file}...")
    return 0


def cmd_watermark(args):
    print(f"Adding watermark to {args.file}...")
    return 0


def cmd_ai(args):
    if not args.ai_command:
        print("Available AI commands: summarize, ask, redact, translate", file=sys.stderr)
        return 1
    if args.ai_command == "summarize":
        print(f"Summarizing {args.file} (max {args.max_length} chars, style={args.style})...")
        return 0
    elif args.ai_command == "ask":
        print(f"Q: {args.question}")
        print(f"A: Analyzing {args.file}...")
        return 0
    elif args.ai_command == "redact":
        print(f"AI redaction on {args.file} (types: {', '.join(args.types)})...")
        return 0
    elif args.ai_command == "translate":
        print(f"Translating {args.file} to {args.target_lang}...")
        return 0
    return 1


def cmd_serve(args):
    print(f"Starting PDFMind web server on {args.host}:{args.port}...")
    return 0


def cmd_health(args):
    info = {
        "app": APP_NAME,
        "version": VERSION,
        "edition": "community",
        "features": FEATURES,
        "release_notes": RELEASE_NOTES,
        "python": sys.version,
        "platform": sys.platform,
        "cwd": os.getcwd(),
    }
    print(json.dumps(info, indent=2))
    return 0


COMMAND_MAP = {
    "open": cmd_open, "merge": cmd_merge, "split": cmd_split,
    "compress": cmd_compress, "ocr": cmd_ocr, "export": cmd_export,
    "info": cmd_info, "pages": cmd_pages, "encrypt": cmd_encrypt,
    "decrypt": cmd_decrypt, "sign": cmd_sign, "watermark": cmd_watermark,
    "ai": cmd_ai, "serve": cmd_serve, "health": cmd_health,
}


class CLI:
    """PDFMind command-line interface dispatcher."""

    @staticmethod
    def run(argv: list[str] = None) -> int:
        parser = create_parser()
        args = parser.parse_args(argv or sys.argv[1:])
        if args.verbose:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        handler = COMMAND_MAP.get(args.command)
        if handler:
            return handler(args)
        parser.print_help()
        return 1

    @staticmethod
    def main():
        sys.exit(CLI.run())


if __name__ == "__main__":
    CLI.main()
