"""PDFMind AI — Ultimate PDF Editor
Entry point for native Python/tkinter application.
"""
import sys
import os
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('pdfmind')


def main():
    parser = argparse.ArgumentParser(
        prog='PDFMind',
        description='PDFMind AI — Ultimate PDF Editor (Microsoft Acquisition Candidate)'
    )
    parser.add_argument('file', nargs='?', help='PDF file to open')
    parser.add_argument('--headless', action='store_true', help='Run without GUI')
    parser.add_argument('--ai-model', default=None, help='Path to AI model')
    parser.add_argument('--port', type=int, default=5000, help='Web API port')
    parser.add_argument('--vulkan', action='store_true', help='Use Vulkan iGPU')
    parser.add_argument('--local', dest='local_mode', action='store_true', default=True,
                        help='Use local-only processing (default)')
    parser.add_argument('--allow-network', dest='local_mode', action='store_false',
                        help='Allow optional cloud and remote AI integrations')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG','INFO','WARNING','ERROR'])
    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.log_level))
    os.environ['PDFMIND_LOCAL_MODE'] = '1' if args.local_mode else '0'
    logger.info('Local-only mode: %s', 'enabled' if args.local_mode else 'disabled')

    if args.headless:
        _run_headless(args)
    else:
        _run_gui(args)


def _run_headless(args):
    """Start Flask web server only."""
    logger.info("Starting PDFMind headless server...")
    from web_app.api.app import create_app
    app = create_app()
    app.run(host='0.0.0.0', port=args.port, debug=False)


def _run_gui(args):
    """Start native tkinter GUI."""
    logger.info("Starting PDFMind GUI...")
    try:
        import tkinter as tk
        from ui.themes.theme import apply_theme
        root = tk.Tk()
        root.title("PDFMind AI — Ultimate PDF Editor")
        root.geometry("1400x900")
        root.minsize(1024, 768)
        apply_theme(root)
        if args.file:
            _open_file(root, args.file)
        root.mainloop()
    except ImportError as e:
        logger.error(f"GUI dependencies missing: {e}")
        print("GUI not available. Run with --headless for web-only mode.")
        sys.exit(1)


def _open_file(root, filepath):
    """Open a PDF file in the editor."""
    try:
        from services.pdf_engine import PDFEngine
        engine = PDFEngine()
        doc = engine.load(filepath)
        logger.info(f"Loaded: {filepath} ({len(doc.pages)} pages)")
    except Exception as e:
        logger.error(f"Failed to open {filepath}: {e}")


if __name__ == '__main__':
    main()
