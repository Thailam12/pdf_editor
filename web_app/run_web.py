"""PDFMind AI — Web Application Runner
Flask backend + React frontend.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from web_app.api.app import create_app

def main():
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    print(f"\n  PDFMind AI Web Editor")
    print(f"  http://localhost:{port}")
    print(f"  Press Ctrl+C to stop\n")
    app.run(host='0.0.0.0', port=port, debug=debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()
