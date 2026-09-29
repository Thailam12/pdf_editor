"""PDF Renderer — Software, D2D, text, image rendering."""
try:
    from .software_renderer import SoftwareRenderer
except ImportError:  # pragma: no cover
    from engine.renderer.software_renderer import SoftwareRenderer
