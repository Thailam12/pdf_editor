"""PDFMind AI Tasks — Summarizer, QA, PII detection, OCR, forms, compare, translate, proofread."""
try:
    from .pdf_summarizer import PDFSummarizer
    from .pdf_question_answerer import PDFQuestionAnswerer
    from .pii_detector import PIIDetector
    from .ocr_corrector import OCRCorrector
    from .form_extractor import FormExtractor
    from .document_comparator import DocumentComparator
    from .pdf_translator import PDFTranslator
    from .proofreader import Proofreader
except ImportError:  # pragma: no cover
    from ai_model.tasks.pdf_summarizer import PDFSummarizer
    from ai_model.tasks.pdf_question_answerer import PDFQuestionAnswerer
    from ai_model.tasks.pii_detector import PIIDetector
    from ai_model.tasks.ocr_corrector import OCRCorrector
    from ai_model.tasks.form_extractor import FormExtractor
    from ai_model.tasks.document_comparator import DocumentComparator
    from ai_model.tasks.pdf_translator import PDFTranslator
    from ai_model.tasks.proofreader import Proofreader
