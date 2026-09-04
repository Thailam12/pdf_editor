import argparse
import json
import io
from contextlib import redirect_stdout

from win32.integrations.developer.cli import VERSION, cmd_health


def test_health_output_reports_release_features():
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result = cmd_health(argparse.Namespace())

    assert result == 0
    payload = json.loads(buffer.getvalue())
    assert payload["version"] == "2026.4"
    assert payload["edition"] == "community"
    assert "ai" in payload["features"]
    assert "ocr" in payload["features"]
    assert VERSION == "2026.4"
