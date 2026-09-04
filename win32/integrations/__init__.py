"""PDFMind Integration & Ecosystem layer.

Provides cloud storage, Office interop, developer tools, printing,
and import/export integrations that make PDFMind indispensable.
"""

from .cloud import GoogleDriveIntegration, DropboxIntegration, BoxIntegration, WebDAVIntegration
from .office import WordImporter, ExcelImporter, PowerPointImporter, OutlookIntegration
from .printing import PrintManager, VirtualPDFPrinter, LargeFormatPlotter
from .import_export import EPUBConverter, DjVuImporter, TIFFConverter, SVGConverter, MarkdownConverter

__all__ = [
    "GoogleDriveIntegration", "DropboxIntegration", "BoxIntegration", "WebDAVIntegration",
    "WordImporter", "ExcelImporter", "PowerPointImporter", "OutlookIntegration",
    "RESTAPIServer", "CLI", "PythonSDK", "JavaScriptSDK", "MCPServer",
    "PrintManager", "VirtualPDFPrinter", "LargeFormatPlotter",
    "EPUBConverter", "DjVuImporter", "TIFFConverter", "SVGConverter", "MarkdownConverter",
]


def __getattr__(name):
    if name in {"RESTAPIServer", "CLI", "PythonSDK", "JavaScriptSDK", "MCPServer"}:
        from . import developer
        return getattr(developer, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
