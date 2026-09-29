"""PDFMind AI Model — 100M Parameter Transformer with QLoRA.
Train, fine-tune, distill, export, and run inference on integrated graphics.
"""
__version__ = "2026.6"
try:
    from .config import PDFMindConfig
    from .model import PDFMind
except ImportError:  # pragma: no cover
    from ai_model.config import PDFMindConfig
    from ai_model.model import PDFMind
