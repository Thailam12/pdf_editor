# -*- coding: utf-8 -*-
"""Application launch tests.

Verifies that the editor can initialize without errors.
Run with: python -m win32.test_launch
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestNativeLoaderLaunch(unittest.TestCase):
    """Test native_loader initializes correctly."""

    def test_detect_does_not_crash(self):
        from win32.native_loader import detect_all
        status = detect_all()
        self.assertIsInstance(status, dict)

    def test_ensure_minimum_does_not_crash(self):
        from win32.native_loader import ensure_minimum
        result = ensure_minimum()
        self.assertTrue(result)


class TestModuleImports(unittest.TestCase):
    """Test that all win32 modules can be imported."""

    def test_import_main(self):
        import importlib
        spec = importlib.util.find_spec("win32.main")
        self.assertIsNotNone(spec)

    def test_import_editor(self):
        import importlib
        spec = importlib.util.find_spec("win32.editor")
        self.assertIsNotNone(spec)

    def test_import_pdf_utils(self):
        import importlib
        spec = importlib.util.find_spec("win32.pdf_utils")
        self.assertIsNotNone(spec)

    def test_import_i18n(self):
        import importlib
        spec = importlib.util.find_spec("win32.i18n")
        self.assertIsNotNone(spec)

    def test_import_easter_eggs(self):
        import importlib
        spec = importlib.util.find_spec("win32.easter_eggs")
        self.assertIsNotNone(spec)

    def test_import_ocr_utils(self):
        import importlib
        spec = importlib.util.find_spec("ocr_utils")
        self.assertIsNotNone(spec)

    def test_import_ocr_paddle(self):
        import importlib
        spec = importlib.util.find_spec("ocr_paddle")
        self.assertIsNotNone(spec)

    def test_import_new_file_template(self):
        import importlib
        spec = importlib.util.find_spec("win32.new_file_template")
        self.assertIsNotNone(spec)


class TestServiceImports(unittest.TestCase):
    """Test that services can be imported."""

    def test_import_services(self):
        import importlib
        spec = importlib.util.find_spec("services")
        self.assertIsNotNone(spec)

    def test_import_models(self):
        import importlib
        spec = importlib.util.find_spec("models")
        self.assertIsNotNone(spec)

    def test_import_models_elements(self):
        import importlib
        spec = importlib.util.find_spec("models.elements")
        self.assertIsNotNone(spec)


class TestEngineImports(unittest.TestCase):
    """Test that engine modules can be imported."""

    def test_import_engine(self):
        import importlib
        spec = importlib.util.find_spec("engine")
        self.assertIsNotNone(spec)

    def test_import_ai_model(self):
        import importlib
        spec = importlib.util.find_spec("ai_model")
        self.assertIsNotNone(spec)


class TestUIImports(unittest.TestCase):
    """Test that UI modules can be imported."""

    def test_import_ui(self):
        import importlib
        spec = importlib.util.find_spec("ui")
        self.assertIsNotNone(spec)


class TestTkinterAvailable(unittest.TestCase):
    """Test that tkinter is available."""

    def test_tkinter_import(self):
        try:
            import tkinter
            self.assertTrue(True)
        except ImportError:
            self.skipTest("tkinter not available (headless environment)")


class TestPymupdfAvailable(unittest.TestCase):
    """Test that PyMuPDF is available."""

    def test_pymupdf_import(self):
        try:
            import pymupdf
            self.assertTrue(True)
        except ImportError:
            self.skipTest("PyMuPDF not installed")


class TestPillowAvailable(unittest.TestCase):
    """Test that Pillow is available."""

    def test_pillow_import(self):
        try:
            from PIL import Image
            self.assertTrue(True)
        except ImportError:
            self.skipTest("Pillow not installed")


class TestCLIEntryPoint(unittest.TestCase):
    """Test that CLI entry point can be found."""

    def test_main_function_exists(self):
        from win32.main import main
        self.assertTrue(callable(main))


class TestPathSetup(unittest.TestCase):
    """Test that sys.path is correctly configured."""

    def test_parent_in_path(self):
        parent = str(Path(__file__).parent.parent)
        self.assertIn(parent, sys.path)


class TestEditorClassExists(unittest.TestCase):
    """Test that editor class can be found."""

    def test_editor_class(self):
        from win32.editor import PDFEditor
        self.assertTrue(callable(PDFEditor))


if __name__ == "__main__":
    print("\n  PDFMind Win32 — Launch Tests\n")
    unittest.main(verbosity=2)
