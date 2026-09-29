import argparse
import json
import io
from contextlib import redirect_stdout

from win32.integrations.developer.cli import VERSION, cmd_health, cmd_encrypt
from win32.integrations.developer.cli import cmd_validate


def test_health_output_reports_release_features():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = cmd_health(argparse.Namespace())

    assert result == 0
    payload = json.loads(buffer.getvalue())
    assert payload["version"] == "2026.6"
    assert payload["edition"] == "community"
    assert "ai" in payload["features"]
    assert "ocr" in payload["features"]
    assert VERSION == "2026.6"


def test_validate_reports_pdf_health(tmp_path):
    import pymupdf

    pdf_path = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = cmd_validate(argparse.Namespace(file=str(pdf_path), json=True))

    assert result == 0
    payload = json.loads(buffer.getvalue())
    assert payload["valid"] is True
    assert payload["pages"] == 1


def test_legacy_encrypt_command_warns_and_still_runs(capsys):
    result = cmd_encrypt(argparse.Namespace(file="example.pdf", password="secret", output=None, user_password=None, perms=["print"]))
    captured = capsys.readouterr()

    assert result == 0
    assert "deprecated" in captured.err.lower()
