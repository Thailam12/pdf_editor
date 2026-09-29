"""PDF Parser — Document parsing, object model, content streams, fonts."""
try:
    from .pdf_parser import PDFParser
    from .object_model import Document, Page
except ImportError:  # pragma: no cover
    from engine.parser.pdf_parser import PDFParser
    from engine.parser.object_model import Document, Page
