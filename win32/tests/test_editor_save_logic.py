import os
import tempfile
import unittest

from win32.editor import PDFEditor


class SaveBehaviorTests(unittest.TestCase):
    def make_editor(self):
        return PDFEditor.__new__(PDFEditor)

    def test_temp_document_prompts_save_as(self):
        editor = self.make_editor()
        editor.is_temp_document = True
        editor.current_pdf = "C:/tmp/temp.pdf"

        self.assertTrue(editor._should_prompt_save_as())

    def test_existing_document_saves_over_original(self):
        editor = self.make_editor()
        editor.is_temp_document = False
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            temp_path = handle.name
        try:
            editor.current_pdf = temp_path
            self.assertFalse(editor._should_prompt_save_as())
        finally:
            os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
