"""Developer integration layer for PDFMind."""

__all__ = ["RESTAPIServer", "CLI", "PythonSDK", "JavaScriptSDK", "MCPServer"]


def __getattr__(name):
	if name == "RESTAPIServer":
		from .rest_api import RESTAPIServer
		return RESTAPIServer
	if name == "CLI":
		from .cli import CLI
		return CLI
	if name == "PythonSDK":
		from .sdk_python import PythonSDK
		return PythonSDK
	if name == "JavaScriptSDK":
		from .sdk_javascript import JavaScriptSDK
		return JavaScriptSDK
	if name == "MCPServer":
		from .mcp_server import MCPServer
		return MCPServer
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
