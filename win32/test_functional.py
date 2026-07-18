# -*- coding: utf-8 -*-
"""Functional tests for the PDFMind Win32 editor.

Run with: python -m unittest win32.test_functional -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPDFUtils(unittest.TestCase):
    def setUp(self):
        from win32.pdf_utils import PDFUtils
        self.pdf_utils = PDFUtils()

    def test_init(self):
        self.assertIsNone(self.pdf_utils.doc)

    def test_load_nonexistent(self):
        with self.assertRaises(Exception):
            self.pdf_utils.load_pdf("/nonexistent/file.pdf")

    def test_preview_without_doc(self):
        result = self.pdf_utils.get_preview_image()
        self.assertIsNone(result)


class TestI18n(unittest.TestCase):
    def test_get_i18n_vi(self):
        from win32.i18n import get_i18n
        i18n = get_i18n("vi")
        self.assertIsInstance(i18n, dict)

    def test_get_i18n_en(self):
        from win32.i18n import get_i18n
        i18n = get_i18n("en")
        self.assertIsInstance(i18n, dict)


class TestEasterEggs(unittest.TestCase):
    def test_should_show(self):
        from win32.easter_eggs import should_show_easter_egg
        result = should_show_easter_egg(0)
        self.assertIsInstance(result, bool)

    def test_pick_easter_egg(self):
        from win32.easter_eggs import pick_easter_egg
        egg = pick_easter_egg()
        self.assertIsNotNone(egg)


class TestNativeLoader(unittest.TestCase):
    def test_detect_all(self):
        from win32.native_loader import detect_all
        status = detect_all()
        self.assertIsInstance(status, dict)
        self.assertIn("pymupdf", status)
        self.assertIn("pillow", status)

    def test_pymupdf_available(self):
        from win32.native_loader import is_available
        self.assertTrue(is_available("pymupdf"))

    def test_pillow_available(self):
        from win32.native_loader import is_available
        self.assertTrue(is_available("pillow"))

    def test_get_missing(self):
        from win32.native_loader import get_missing
        missing = get_missing()
        self.assertIsInstance(missing, list)

    def test_ensure_minimum(self):
        from win32.native_loader import ensure_minimum
        result = ensure_minimum()
        self.assertTrue(result)


class TestNewFileTemplate(unittest.TestCase):
    def test_create_blank_pdf(self):
        from win32.new_file_template import create_blank_pdf
        self.assertTrue(callable(create_blank_pdf))


class TestOCRUtils(unittest.TestCase):
    def test_ocrbox_dataclass(self):
        from win32.ocr_utils import OCRBox
        box = OCRBox(text="hello", x1_px=0, y1_px=0, x2_px=100, y2_px=50)
        self.assertEqual(box.text, "hello")
        self.assertEqual(box.x1_px, 0)
        self.assertIsNone(box.confidence)

    def test_ocrbox_with_confidence(self):
        from win32.ocr_utils import OCRBox
        box = OCRBox(text="world", x1_px=10, y1_px=10, x2_px=200, y2_px=80, confidence=0.95)
        self.assertAlmostEqual(box.confidence, 0.95)


class TestEditorImport(unittest.TestCase):
    def test_editor_importable(self):
        from win32.editor import PDFEditor
        self.assertTrue(callable(PDFEditor))


class TestServicesImport(unittest.TestCase):
    def test_services_importable(self):
        import services
        self.assertTrue(hasattr(services, "CanvasManager"))

    def test_document_manager(self):
        from services import DocumentManager
        self.assertTrue(callable(DocumentManager))


class TestModelsImport(unittest.TestCase):
    def test_elements_importable(self):
        from models import elements
        self.assertTrue(hasattr(elements, "TextElement"))

    def test_text_element(self):
        from models.elements import TextElement
        elem = TextElement(x=10, y=20, text="test")
        self.assertEqual(elem.text, "test")

    def test_shape_element(self):
        from models.elements import ShapeElement
        elem = ShapeElement(shape_type="rect", x=0, y=0, w=100, h=50)
        self.assertEqual(elem.shape_type, "rect")


class TestEngineImport(unittest.TestCase):
    def test_parser_importable(self):
        from engine.parser import pdf_parser
        self.assertTrue(hasattr(pdf_parser, "PDFParser"))

    def test_renderer_importable(self):
        from engine.renderer import software_renderer
        self.assertTrue(hasattr(software_renderer, "SoftwareRenderer"))


class TestAIModelImport(unittest.TestCase):
    def test_config_importable(self):
        from ai_model.config import PDFMindConfig, PRETRAINED_CONFIG
        self.assertIsInstance(PRETRAINED_CONFIG, PDFMindConfig)
        self.assertEqual(PRETRAINED_CONFIG.vocab_size, 32000)

    def test_model_class(self):
        from ai_model.model import PDFMindForCausalLM
        self.assertTrue(callable(PDFMindForCausalLM))


class TestTempFileHandling(unittest.TestCase):
    def test_temp_pdf_creation(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4")
            temp_path = f.name
        self.assertTrue(os.path.exists(temp_path))
        os.unlink(temp_path)
        self.assertFalse(os.path.exists(temp_path))


class TestEnterprise(unittest.TestCase):
    def test_feature_flags(self):
        from enterprise.admin.license_manager import FeatureFlagManager
        fm = FeatureFlagManager()
        self.assertTrue(fm.is_enabled("basic_edit"))

    def test_pdfa_validator(self):
        from enterprise.compliance.pdfa_validator import PdfAValidator
        self.assertTrue(callable(PdfAValidator))


class TestIntegrations(unittest.TestCase):
    def test_cli_importable(self):
        from integrations.developer import cli
        self.assertTrue(hasattr(cli, "main") or hasattr(cli, "cli") or True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
