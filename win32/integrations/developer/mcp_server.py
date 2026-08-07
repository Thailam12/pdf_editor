"""MCP Server for AI agents: tool definitions, resource providers, and prompt templates for PDF operations."""

import json
import logging
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    name: str = ""
    description: str = ""
    input_schema: dict = field(default_factory=dict)
    handler: Optional[Callable] = None
    annotations: dict = field(default_factory=dict)


@dataclass
class MCPResource:
    uri: str = ""
    name: str = ""
    description: str = ""
    mime_type: str = "application/json"
    handler: Optional[Callable] = None


@dataclass
class MCPPrompt:
    name: str = ""
    description: str = ""
    arguments: list[dict] = field(default_factory=list)
    handler: Optional[Callable] = None


@dataclass
class MCPMessage:
    jsonrpc: str = "2.0"
    id: Any = None
    method: str = ""
    params: dict = field(default_factory=dict)


class MCPServer:
    """Model Context Protocol server providing PDFMind tools and resources to AI agents."""

    PROTOCOL_VERSION = "2024-11-05"
    SERVER_NAME = "pdfmind-mcp"
    SERVER_VERSION = "2.1"

    def __init__(self):
        self._tools: dict[str, MCPTool] = {}
        self._resources: dict[str, MCPResource] = {}
        self._prompts: dict[str, MCPPrompt] = {}
        self._resource_templates: list[dict] = []
        self._register_default_tools()
        self._register_default_resources()
        self._register_default_prompts()
        self._request_id = 0

    def _next_id(self):
        self._request_id += 1
        return self._request_id

    def _register_default_tools(self):
        tools = [
            MCPTool(
                name="pdfmind_open",
                description="Open a PDF document and get its metadata, page count, and structure",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the PDF file"},
                    },
                    "required": ["file_path"],
                },
            ),
            MCPTool(
                name="pdfmind_read_page",
                description="Read the text content of a specific page in a PDF",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "page_number": {"type": "integer", "description": "Page number (1-indexed)"},
                    },
                    "required": ["file_path", "page_number"],
                },
            ),
            MCPTool(
                name="pdfmind_read_all",
                description="Read the full text content of all pages in a PDF",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "max_pages": {"type": "integer", "description": "Maximum pages to read", "default": 50},
                    },
                    "required": ["file_path"],
                },
            ),
            MCPTool(
                name="pdfmind_merge",
                description="Merge multiple PDF files into a single document",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_paths": {"type": "array", "items": {"type": "string"}, "description": "PDF files to merge"},
                        "output_path": {"type": "string", "description": "Output file path"},
                    },
                    "required": ["file_paths", "output_path"],
                },
            ),
            MCPTool(
                name="pdfmind_split",
                description="Split a PDF into separate files by page ranges",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "page_ranges": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "integer"}},
                            "description": "Array of [start, end] page ranges",
                        },
                        "output_dir": {"type": "string", "description": "Output directory"},
                    },
                    "required": ["file_path", "output_dir"],
                },
            ),
            MCPTool(
                name="pdfmind_compress",
                description="Compress a PDF to reduce file size",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "output_path": {"type": "string"},
                        "level": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"},
                    },
                    "required": ["file_path"],
                },
            ),
            MCPTool(
                name="pdfmind_extract_text",
                description="Extract all text from a PDF document",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "pages": {
                            "type": "array", "items": {"type": "integer"},
                            "description": "Specific pages to extract (1-indexed)",
                        },
                    },
                    "required": ["file_path"],
                },
            ),
            MCPTool(
                name="pdfmind_search_text",
                description="Search for text within a PDF document",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "query": {"type": "string", "description": "Text to search for"},
                        "case_sensitive": {"type": "boolean", "default": False},
                    },
                    "required": ["file_path", "query"],
                },
            ),
            MCPTool(
                name="pdfmind_annotate",
                description="Add annotations (highlights, notes, underlines) to a PDF page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "page_number": {"type": "integer"},
                        "annotation_type": {"type": "string", "enum": ["highlight", "note", "underline", "strikethrough"]},
                        "text": {"type": "string", "description": "Text to annotate or note content"},
                        "x": {"type": "number"}, "y": {"type": "number"},
                        "width": {"type": "number"}, "height": {"type": "number"},
                        "color": {"type": "string", "default": "FFFF00"},
                    },
                    "required": ["file_path", "page_number", "annotation_type"],
                },
            ),
            MCPTool(
                name="pdfmind_redact",
                description="Redact (permanently remove) sensitive content from a PDF",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "output_path": {"type": "string"},
                        "patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Regex patterns to redact",
                        },
                        "page_numbers": {
                            "type": "array", "items": {"type": "integer"},
                            "description": "Pages to redact (empty = all)",
                        },
                    },
                    "required": ["file_path", "patterns"],
                },
            ),
            MCPTool(
                name="pdfmind_encrypt",
                description="Encrypt a PDF with a password",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "output_path": {"type": "string"},
                        "password": {"type": "string", "description": "Encryption password"},
                    },
                    "required": ["file_path", "password"],
                },
            ),
            MCPTool(
                name="pdfmind_add_watermark",
                description="Add a text watermark to all pages of a PDF",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "output_path": {"type": "string"},
                        "text": {"type": "string", "description": "Watermark text"},
                        "opacity": {"type": "number", "default": 0.3},
                        "rotation": {"type": "number", "default": 45},
                    },
                    "required": ["file_path", "text"],
                },
            ),
            MCPTool(
                name="pdfmind_summarize",
                description="Generate a summary of the PDF content using AI",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "max_length": {"type": "integer", "default": 500},
                        "style": {"type": "string", "enum": ["brief", "detailed", "bullet"], "default": "brief"},
                    },
                    "required": ["file_path"],
                },
            ),
            MCPTool(
                name="pdfmind_ask",
                description="Ask a question about a PDF document and get an answer based on its content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "question": {"type": "string", "description": "Question to ask about the document"},
                    },
                    "required": ["file_path", "question"],
                },
            ),
            MCPTool(
                name="pdfmind_get_info",
                description="Get detailed information about a PDF (metadata, page count, file size)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                    },
                    "required": ["file_path"],
                },
            ),
        ]
        for tool in tools:
            self._tools[tool.name] = tool

    def _register_default_resources(self):
        resources = [
            MCPResource(
                uri="pdfmind://documents",
                name="PDF Documents",
                description="List of loaded PDF documents",
            ),
            MCPResource(
                uri="pdfmind://capabilities",
                name="PDFMind Capabilities",
                description="Available PDF operations and features",
            ),
            MCPResource(
                uri="pdfmind://health",
                name="System Health",
                description="PDFMind system health status",
            ),
        ]
        for res in resources:
            self._resources[res.uri] = res

        self._resource_templates = [
            {
                "uriTemplate": "pdfmind://documents/{id}",
                "name": "PDF Document",
                "description": "A specific PDF document by ID",
                "mimeType": "application/json",
            },
            {
                "uriTemplate": "pdfmind://documents/{id}/page/{page}",
                "name": "PDF Page Content",
                "description": "Content of a specific page in a PDF",
                "mimeType": "text/plain",
            },
        ]

    def _register_default_prompts(self):
        prompts = [
            MCPPrompt(
                name="summarize_pdf",
                description="Get a summary of a PDF document",
                arguments=[
                    {"name": "file_path", "description": "Path to the PDF file", "required": True},
                    {"name": "style", "description": "Summary style: brief, detailed, or bullet", "required": False},
                ],
            ),
            MCPPrompt(
                name="analyze_pdf",
                description="Perform a detailed analysis of a PDF",
                arguments=[
                    {"name": "file_path", "description": "Path to the PDF file", "required": True},
                    {"name": "focus", "description": "Analysis focus area", "required": False},
                ],
            ),
            MCPPrompt(
                name="redact_pii",
                description="Identify and redact personally identifiable information from a PDF",
                arguments=[
                    {"name": "file_path", "description": "Path to the PDF file", "required": True},
                    {"name": "pii_types", "description": "Types of PII to redact", "required": False},
                ],
            ),
            MCPPrompt(
                name="convert_to_markdown",
                description="Convert a PDF to well-formatted Markdown",
                arguments=[
                    {"name": "file_path", "description": "Path to the PDF file", "required": True},
                    {"name": "preserve_tables", "description": "Preserve table formatting", "required": False},
                ],
            ),
            MCPPrompt(
                name="extract_key_info",
                description="Extract key information (dates, names, amounts, etc.) from a PDF",
                arguments=[
                    {"name": "file_path", "description": "Path to the PDF file", "required": True},
                    {"name": "categories", "description": "Information categories to extract", "required": False},
                ],
            ),
            MCPPrompt(
                name="compare_pdfs",
                description="Compare two PDFs and describe the differences",
                arguments=[
                    {"name": "file_path_a", "description": "Path to the first PDF", "required": True},
                    {"name": "file_path_b", "description": "Path to the second PDF", "required": True},
                ],
            ),
        ]
        for prompt in prompts:
            self._prompts[prompt.name] = prompt

    def register_tool(self, tool: MCPTool):
        self._tools[tool.name] = tool

    def register_resource(self, resource: MCPResource):
        self._resources[resource.uri] = resource

    def register_prompt(self, prompt: MCPPrompt):
        self._prompts[prompt.name] = prompt

    def handle_request(self, request: dict) -> dict:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")
        if method == "initialize":
            return self._handle_initialize(req_id, params)
        elif method == "notifications/initialized":
            return {}
        elif method == "tools/list":
            return self._handle_tools_list(req_id)
        elif method == "tools/call":
            return self._handle_tools_call(req_id, params)
        elif method == "resources/list":
            return self._handle_resources_list(req_id)
        elif method == "resources/read":
            return self._handle_resources_read(req_id, params)
        elif method == "resources/templates/list":
            return self._handle_resource_templates(req_id)
        elif method == "prompts/list":
            return self._handle_prompts_list(req_id)
        elif method == "prompts/get":
            return self._handle_prompts_get(req_id, params)
        elif method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}
        else:
            return self._error_response(req_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, req_id, params):
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {},
                    "resources": {"listChanged": True},
                    "prompts": {"listChanged": True},
                },
                "serverInfo": {"name": self.SERVER_NAME, "version": self.SERVER_VERSION},
            },
        }

    def _handle_tools_list(self, req_id):
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
                **t.annotations,
            }
            for t in self._tools.values()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    def _handle_tools_call(self, req_id, params):
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        tool = self._tools.get(tool_name)
        if not tool:
            return self._error_response(req_id, -32602, f"Unknown tool: {tool_name}")
        if tool.handler:
            try:
                result = tool.handler(arguments)
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]},
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0", "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "isError": True},
                }
        result = self._execute_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, default=str)}]},
        }

    def _execute_tool(self, tool_name: str, args: dict) -> dict:
        if tool_name == "pdfmind_get_info":
            return {"status": "ok", "file": args.get("file_path"), "tool": tool_name}
        elif tool_name == "pdfmind_read_all":
            return {"status": "ok", "file": args.get("file_path"), "text": "[Document text content]", "tool": tool_name}
        elif tool_name == "pdfmind_summarize":
            return {"status": "ok", "summary": "Summary of the document content.", "tool": tool_name}
        elif tool_name == "pdfmind_ask":
            return {"status": "ok", "answer": f"Answer to: {args.get('question', '')}", "tool": tool_name}
        return {"status": "ok", "tool": tool_name, "message": "Handler not yet implemented"}

    def _handle_resources_list(self, req_id):
        resources = [
            {"uri": r.uri, "name": r.name, "description": r.description, "mimeType": r.mime_type}
            for r in self._resources.values()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": resources}}

    def _handle_resources_read(self, req_id, params):
        uri = params.get("uri", "")
        resource = self._resources.get(uri)
        if not resource:
            return self._error_response(req_id, -32602, f"Unknown resource: {uri}")
        if uri == "pdfmind://capabilities":
            data = {
                "tools": list(self._tools.keys()),
                "prompts": list(self._prompts.keys()),
                "version": self.SERVER_VERSION,
            }
        elif uri == "pdfmind://health":
            data = {"status": "healthy", "version": self.SERVER_VERSION}
        else:
            data = {"uri": uri, "name": resource.name}
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {"contents": [{"uri": uri, "mimeType": resource.mime_type,
                                      "text": json.dumps(data)}]},
        }

    def _handle_resource_templates(self, req_id):
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resourceTemplates": self._resource_templates}}

    def _handle_prompts_list(self, req_id):
        prompts = [
            {"name": p.name, "description": p.description, "arguments": p.arguments}
            for p in self._prompts.values()
        ]
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": prompts}}

    def _handle_prompts_get(self, req_id, params):
        prompt_name = params.get("name", "")
        arguments = params.get("arguments", {})
        prompt = self._prompts.get(prompt_name)
        if not prompt:
            return self._error_response(req_id, -32602, f"Unknown prompt: {prompt_name}")
        file_path = arguments.get("file_path", "document.pdf")
        if prompt_name == "summarize_pdf":
            style = arguments.get("style", "brief")
            messages = [{
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Please provide a {style} summary of the PDF document at {file_path}. "
                            f"Use the pdfmind_read_all tool to read the document first, then summarize it.",
                },
            }]
        elif prompt_name == "analyze_pdf":
            focus = arguments.get("focus", "general")
            messages = [{
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Analyze the PDF at {file_path} focusing on {focus}. "
                            f"Read the document with pdfmind_read_all, then provide detailed analysis.",
                },
            }]
        elif prompt_name == "redact_pii":
            messages = [{
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Identify and redact PII from {file_path}. "
                            f"Read the document first, identify PII (names, SSNs, emails, phones, addresses, DOB), "
                            f"then use pdfmind_redact to remove them.",
                },
            }]
        elif prompt_name == "compare_pdfs":
            file_b = arguments.get("file_path_b", "document_b.pdf")
            messages = [{
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"Compare PDF {file_path} with {file_b}. Read both and describe all differences.",
                },
            }]
        else:
            messages = [{
                "role": "user",
                "content": {"type": "text", "text": f"Process {file_path} using the {prompt_name} workflow."},
            }]
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {"description": prompt.description, "messages": messages},
        }

    def _error_response(self, req_id, code, message):
        return {
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": code, "message": message},
        }

    def get_tool_schemas_for_claude(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in self._tools.values()
        ]

    def get_tool_schemas_for_openai(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in self._tools.values()
        ]

    def get_capabilities_summary(self) -> dict:
        return {
            "server": self.SERVER_NAME,
            "version": self.SERVER_VERSION,
            "protocol_version": self.PROTOCOL_VERSION,
            "tools_count": len(self._tools),
            "resources_count": len(self._resources),
            "prompts_count": len(self._prompts),
            "tools": list(self._tools.keys()),
        }
