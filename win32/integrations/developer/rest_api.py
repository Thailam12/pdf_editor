"""REST API with OpenAPI 3.0 spec, generous rate limiting, and webhooks."""

import json
import time
import hashlib
import secrets
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    requests_per_minute: int = 200
    requests_per_hour: int = 10000
    requests_per_day: int = 100000
    _minute_counts: dict = field(default_factory=dict)
    _hour_counts: dict = field(default_factory=dict)
    _day_counts: dict = field(default_factory=dict)

    def check(self, client_id: str = "default") -> tuple[bool, dict]:
        now = time.time()
        minute_key = f"{client_id}:{int(now // 60)}"
        hour_key = f"{client_id}:{int(now // 3600)}"
        day_key = f"{client_id}:{int(now // 86400)}"
        self._cleanup(now)
        minute_count = self._minute_counts.get(minute_key, 0)
        hour_count = self._hour_counts.get(hour_key, 0)
        day_count = self._day_counts.get(day_key, 0)
        if minute_count >= self.requests_per_minute:
            return False, {"retry_after": 60 - int(now % 60), "limit": self.requests_per_minute, "remaining": 0}
        if hour_count >= self.requests_per_hour:
            return False, {"retry_after": 3600 - int(now % 3600), "limit": self.requests_per_hour, "remaining": 0}
        if day_count >= self.requests_per_day:
            return False, {"retry_after": 86400 - int(now % 86400), "limit": self.requests_per_day, "remaining": 0}
        self._minute_counts[minute_key] = minute_count + 1
        self._hour_counts[hour_key] = hour_count + 1
        self._day_counts[day_key] = day_count + 1
        return True, {
            "limit": self.requests_per_minute,
            "remaining": self.requests_per_minute - minute_count - 1,
            "reset": int(now) + (60 - int(now % 60)),
        }

    def _cleanup(self, now: float):
        cutoff_min = int(now // 60) - 2
        cutoff_hour = int(now // 3600) - 2
        cutoff_day = int(now // 86400) - 2
        self._minute_counts = {k: v for k, v in self._minute_counts.items()
                               if int(k.split(":")[1]) > cutoff_min}
        self._hour_counts = {k: v for k, v in self._hour_counts.items()
                             if int(k.split(":")[1]) > cutoff_hour}
        self._day_counts = {k: v for k, v in self._day_counts.items()
                            if int(k.split(":")[1]) > cutoff_day}


@dataclass
class Webhook:
    webhook_id: str = ""
    url: str = ""
    events: list[str] = field(default_factory=list)
    secret: str = ""
    is_active: bool = True
    created_at: str = ""
    last_triggered: str = ""
    failure_count: int = 0
    max_failures: int = 5


@dataclass
class APIEndpoint:
    method: str = ""
    path: str = ""
    summary: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    request_schema: dict = field(default_factory=dict)
    response_schema: dict = field(default_factory=dict)
    requires_auth: bool = False
    rate_limit_tier: str = "standard"


@dataclass
class APIResponse:
    status_code: int = 200
    body: Any = None
    headers: dict = field(default_factory=dict)
    error: str = ""


class RESTAPIServer:
    """Free and open-source REST API server with OpenAPI 3.0 spec, rate limiting, and webhooks."""

    VERSION = "1.0.0"

    def __init__(self, title: str = "PDFMind API", description: str = "PDF editing and management API — free and open-source"):
        self.title = title
        self.description = description
        self._rate_limiter = RateLimiter()
        self._webhooks: dict[str, Webhook] = {}
        self._endpoints: list[APIEndpoint] = []
        self._handlers: dict[str, Callable] = {}
        self._register_default_endpoints()

    def _register_default_endpoints(self):
        endpoints = [
            APIEndpoint("POST", "/api/v1/documents/open", "Open a PDF document", tags=["documents"]),
            APIEndpoint("POST", "/api/v1/documents/create", "Create a new document", tags=["documents"]),
            APIEndpoint("GET", "/api/v1/documents/{id}", "Get document info", tags=["documents"]),
            APIEndpoint("DELETE", "/api/v1/documents/{id}", "Delete a document", tags=["documents"]),
            APIEndpoint("GET", "/api/v1/documents/{id}/pages", "List pages", tags=["pages"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/pages", "Add pages", tags=["pages"]),
            APIEndpoint("DELETE", "/api/v1/documents/{id}/pages/{page}", "Delete a page", tags=["pages"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/pages/reorder", "Reorder pages", tags=["pages"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/merge", "Merge with another PDF", tags=["documents"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/split", "Split document", tags=["documents"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/compress", "Compress document", tags=["documents"]),
            APIEndpoint("GET", "/api/v1/documents/{id}/pages/{page}/elements", "List elements", tags=["elements"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/pages/{page}/elements", "Add elements", tags=["elements"]),
            APIEndpoint("PUT", "/api/v1/documents/{id}/pages/{page}/elements/{eid}", "Update element", tags=["elements"]),
            APIEndpoint("DELETE", "/api/v1/documents/{id}/pages/{page}/elements/{eid}", "Delete element", tags=["elements"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/text", "Extract text", tags=["extraction"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/images", "Extract images", tags=["extraction"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/annotations", "Add annotations", tags=["annotations"]),
            APIEndpoint("GET", "/api/v1/documents/{id}/annotations", "List annotations", tags=["annotations"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/redact", "Apply redactions", tags=["security"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/encrypt", "Encrypt document", tags=["security"]),
            APIEndpoint("POST", "/api/v1/documents/{id}/sign", "Digital signature", tags=["security"]),
            APIEndpoint("POST", "/api/v1/ai/summarize", "AI summarization", tags=["ai"]),
            APIEndpoint("POST", "/api/v1/ai/ask", "Ask question about document", tags=["ai"]),
            APIEndpoint("POST", "/api/v1/ai/redact-smart", "Smart AI redaction", tags=["ai"]),
            APIEndpoint("GET", "/api/v1/health", "Health check", tags=["system"]),
            APIEndpoint("GET", "/api/v1/webhooks", "List webhooks", tags=["admin"]),
            APIEndpoint("POST", "/api/v1/webhooks", "Create webhook", tags=["admin"]),
            APIEndpoint("DELETE", "/api/v1/webhooks/{id}", "Delete webhook", tags=["admin"]),
        ]
        self._endpoints.extend(endpoints)

    def register_handler(self, method: str, path: str, handler: Callable):
        route_key = f"{method.upper()}:{path}"
        self._handlers[route_key] = handler

    def create_webhook(self, url: str, events: list[str]) -> Webhook:
        webhook_id = secrets.token_hex(16)
        secret = secrets.token_urlsafe(32)
        wh = Webhook(
            webhook_id=webhook_id, url=url, events=events, secret=secret,
            is_active=True, created_at=datetime.now().isoformat(),
        )
        self._webhooks[webhook_id] = wh
        return wh

    def delete_webhook(self, webhook_id: str) -> bool:
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            return True
        return False

    def list_webhooks(self) -> list[dict]:
        return [
            {"webhook_id": w.webhook_id, "url": w.url, "events": w.events,
             "is_active": w.is_active, "created_at": w.created_at,
             "last_triggered": w.last_triggered, "failure_count": w.failure_count}
            for w in self._webhooks.values()
        ]

    async def trigger_webhooks(self, event: str, payload: dict):
        import aiohttp
        for wh in self._webhooks.values():
            if not wh.is_active or event not in wh.events:
                continue
            try:
                import hmac
                body = json.dumps(payload).encode()
                signature = hmac.new(wh.secret.encode(), body, hashlib.sha256).hexdigest()
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        wh.url, json=payload,
                        headers={"X-PDFMind-Event": event, "X-PDFMind-Signature": signature},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status >= 400:
                            wh.failure_count += 1
                            if wh.failure_count >= wh.max_failures:
                                wh.is_active = False
                                logger.warning(f"Webhook {wh.webhook_id} disabled after {wh.failure_count} failures")
                        else:
                            wh.failure_count = 0
                            wh.last_triggered = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"Webhook delivery failed: {e}")
                wh.failure_count += 1

    def generate_openapi_spec(self) -> dict:
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "description": self.description,
                "version": self.VERSION,
                "contact": {"name": "PDFMind Team"},
                "license": {"name": "MIT"},
            },
            "servers": [
                {"url": "http://localhost:8000", "description": "Local development"},
            ],
            "components": {
                "schemas": {
                    "Document": {"type": "object", "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "page_count": {"type": "integer"},
                        "created_at": {"type": "string", "format": "date-time"},
                    }},
                    "Page": {"type": "object", "properties": {
                        "index": {"type": "integer"},
                        "width": {"type": "number"},
                        "height": {"type": "number"},
                    }},
                    "Element": {"type": "object", "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                        "content": {"type": "string"},
                    }},
                    "Error": {"type": "object", "properties": {
                        "code": {"type": "integer"},
                        "message": {"type": "string"},
                    }},
                },
            },
            "paths": {},
            "tags": [],
        }
        seen_tags = set()
        for ep in self._endpoints:
            if ep.path not in spec["paths"]:
                spec["paths"][ep.path] = {}
            operation = {
                "summary": ep.summary,
                "description": ep.description,
                "tags": ep.tags,
                "responses": {
                    "200": {"description": "Success", "content": {"application/json": {"schema": {"type": "object"}}}},
                    "400": {"description": "Bad Request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    "429": {"description": "Rate limit exceeded"},
                },
            }
            if ep.request_schema:
                operation["requestBody"] = {
                    "content": {"application/json": {"schema": ep.request_schema}},
                }
            spec["paths"][ep.path][ep.method.lower()] = operation
            for tag in ep.tags:
                if tag not in seen_tags:
                    seen_tags.add(tag)
                    spec["tags"].append({"name": tag})
        return spec

    def get_openapi_json(self) -> str:
        return json.dumps(self.generate_openapi_spec(), indent=2)

    def get_api_docs_html(self) -> str:
        return f"""<!DOCTYPE html>
<html><head><title>{self.title} - API Documentation</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head><body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
<script>
SwaggerUIBundle({{
    spec: {self.get_openapi_json()},
    dom_id: '#swagger-ui',
    presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
    layout: "StandaloneLayout"
}});
</script></body></html>"""

    def health_check(self) -> dict:
        return {
            "status": "healthy",
            "version": self.VERSION,
            "timestamp": datetime.now().isoformat(),
            "webhooks": len(self._webhooks),
            "endpoints": len(self._endpoints),
            "license": "MIT",
        }
