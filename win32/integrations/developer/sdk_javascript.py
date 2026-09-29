"""JavaScript SDK for PDFMind: client-side PDF operations via REST API."""

import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

JS_SDK_SOURCE = r"""
/**
 * PDFMind JavaScript SDK — free and open-source (MIT License).
 * Client-side PDF operations via the PDFMind REST API.
 *
 * Usage:
 *   const pdfmind = new PDFMind();
 *   const doc = await pdfmind.documents.open(file);
 *   const text = await pdfmind.documents.extractText(doc.id);
 */

class PDFMind {
    constructor(config = {}) {
        this.baseUrl = config.baseUrl || 'http://localhost:8000';
        this.timeout = config.timeout || 30000;
        this.headers = {
            'Content-Type': 'application/json',
        };
        this.documents = new DocumentAPI(this);
        this.pages = new PageAPI(this);
        this.elements = new ElementAPI(this);
        this.ai = new AIAPI(this);
        this.export = new ExportAPI(this);
    }

    async _request(method, path, body = null, options = {}) {
        const url = `${this.baseUrl}${path}`;
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.timeout);
        try {
            const response = await fetch(url, {
                method,
                headers: { ...this.headers, ...options.headers },
                body: body ? JSON.stringify(body) : null,
                signal: controller.signal,
            });
            clearTimeout(timer);
            if (!response.ok) {
                const error = await response.json().catch(() => ({ message: response.statusText }));
                throw new PDFMindError(error.message || response.statusText, response.status, error);
            }
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                return await response.json();
            }
            return await response.blob();
        } catch (err) {
            clearTimeout(timer);
            if (err instanceof PDFMindError) throw err;
            throw new PDFMindError(err.message, 0, { original: err });
        }
    }

    async health() {
        return this._request('GET', '/api/v1/health');
    }
}

class PDFMindError extends Error {
    constructor(message, statusCode, details) {
        super(message);
        this.name = 'PDFMindError';
        this.statusCode = statusCode;
        this.details = details;
    }
}

class DocumentAPI {
    constructor(client) {
        this.client = client;
    }

    async list(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.client._request('GET', `/api/v1/documents${query ? '?' + query : ''}`);
    }

    async open(file) {
        if (file instanceof File) {
            const formData = new FormData();
            formData.append('file', file);
            return this.client._request('POST', '/api/v1/documents/open', null, {
                headers: { 'Content-Type': 'multipart/form-data' },
                body: formData,
            });
        }
        return this.client._request('POST', '/api/v1/documents/open', { path: file });
    }

    async get(documentId) {
        return this.client._request('GET', `/api/v1/documents/${documentId}`);
    }

    async create(options = {}) {
        return this.client._request('POST', '/api/v1/documents/create', options);
    }

    async delete(documentId) {
        return this.client._request('DELETE', `/api/v1/documents/${documentId}`);
    }

    async merge(documentIds, outputName = 'merged.pdf') {
        return this.client._request('POST', '/api/v1/documents/merge', {
            document_ids: documentIds,
            output_name: outputName,
        });
    }

    async split(documentId, options = {}) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/split`, options);
    }

    async compress(documentId, level = 'medium') {
        return this.client._request('POST', `/api/v1/documents/${documentId}/compress`, { level });
    }

    async extractText(documentId, pageRange = null) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/text`, {
            pages: pageRange,
        });
    }

    async extractImages(documentId) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/images`);
    }

    async getMetadata(documentId) {
        return this.client._request('GET', `/api/v1/documents/${documentId}/metadata`);
    }

    async setMetadata(documentId, metadata) {
        return this.client._request('PUT', `/api/v1/documents/${documentId}/metadata`, metadata);
    }

    async encrypt(documentId, password, options = {}) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/encrypt`, {
            password, ...options,
        });
    }

    async decrypt(documentId, password) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/decrypt`, { password });
    }

    async addWatermark(documentId, options) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/watermark`, options);
    }

    async sign(documentId, options) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/sign`, options);
    }

    async redact(documentId, options) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/redact`, options);
    }

    async download(documentId) {
        return this.client._request('GET', `/api/v1/documents/${documentId}/download`);
    }
}

class PageAPI {
    constructor(client) {
        this.client = client;
    }

    async list(documentId) {
        return this.client._request('GET', `/api/v1/documents/${documentId}/pages`);
    }

    async add(documentId, options = {}) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/pages`, options);
    }

    async remove(documentId, pageIndex) {
        return this.client._request('DELETE', `/api/v1/documents/${documentId}/pages/${pageIndex}`);
    }

    async reorder(documentId, pageOrder) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/pages/reorder`, {
            order: pageOrder,
        });
    }

    async rotate(documentId, pageIndex, angle = 90) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/pages/${pageIndex}/rotate`, {
            angle,
        });
    }

    async duplicate(documentId, pageIndex, count = 1) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/pages/${pageIndex}/duplicate`, {
            count,
        });
    }
}

class ElementAPI {
    constructor(client) {
        this.client = client;
    }

    async list(documentId, pageIndex) {
        return this.client._request('GET', `/api/v1/documents/${documentId}/pages/${pageIndex}/elements`);
    }

    async add(documentId, pageIndex, element) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/pages/${pageIndex}/elements`, element);
    }

    async update(documentId, pageIndex, elementId, updates) {
        return this.client._request('PUT', `/api/v1/documents/${documentId}/pages/${pageIndex}/elements/${elementId}`, updates);
    }

    async remove(documentId, pageIndex, elementId) {
        return this.client._request('DELETE', `/api/v1/documents/${documentId}/pages/${pageIndex}/elements/${elementId}`);
    }
}

class AIAPI {
    constructor(client) {
        this.client = client;
    }

    async summarize(documentId, options = {}) {
        return this.client._request('POST', '/api/v1/ai/summarize', { document_id: documentId, ...options });
    }

    async ask(documentId, question) {
        return this.client._request('POST', '/api/v1/ai/ask', { document_id: documentId, question });
    }

    async redactSmart(documentId, types = ['pii', 'financial']) {
        return this.client._request('POST', '/api/v1/ai/redact-smart', { document_id: documentId, types });
    }

    async translate(documentId, targetLang) {
        return this.client._request('POST', '/api/v1/ai/translate', { document_id: documentId, target_lang: targetLang });
    }

    async extractEntities(documentId) {
        return this.client._request('POST', '/api/v1/ai/extract-entities', { document_id: documentId });
    }
}

class ExportAPI {
    constructor(client) {
        this.client = client;
    }

    async toFormat(documentId, format, options = {}) {
        return this.client._request('POST', `/api/v1/documents/${documentId}/export`, { format, ...options });
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PDFMind, PDFMindError };
}
if (typeof window !== 'undefined') {
    window.PDFMind = PDFMind;
}
"""


class JavaScriptSDK:
    """Generates and manages the JavaScript SDK for PDFMind."""

    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url

    def get_source(self) -> str:
        return JS_SDK_SOURCE

    def get_minified(self) -> str:
        source = JS_SDK_SOURCE
        lines = [line.strip() for line in source.split("\n") if line.strip() and not line.strip().startswith("//")]
        return " ".join(lines)

    def get_html_example(self) -> str:
        return """<!DOCTYPE html>
<html>
<head><title>PDFMind JS SDK Demo</title></head>
<body>
<h1>PDFMind JavaScript SDK Demo</h1>
<input type="file" id="fileInput" accept=".pdf">
<button onclick="openFile()">Open PDF</button>
<button onclick="compressFile()">Compress</button>
<button onclick="extractText()">Extract Text</button>
<button onclick="aiSummarize()">AI Summarize</button>
<pre id="output"></pre>
<script src="pdfmind-sdk.js"></script>
<script>
const pdfmind = new PDFMind();
let currentDocId = null;

async function openFile() {
    const file = document.getElementById('fileInput').files[0];
    if (!file) return;
    const doc = await pdfmind.documents.open(file);
    currentDocId = doc.id;
    log(`Opened: ${doc.title} (${doc.page_count} pages)`);
}

async function compressFile() {
    if (!currentDocId) return;
    const result = await pdfmind.documents.compress(currentDocId, 'high');
    log(`Compressed: ${JSON.stringify(result)}`);
}

async function extractText() {
    if (!currentDocId) return;
    const result = await pdfmind.documents.extractText(currentDocId);
    log(`Text: ${result.text}`);
}

async function aiSummarize() {
    if (!currentDocId) return;
    const result = await pdfmind.ai.summarize(currentDocId, { style: 'brief' });
    log(`Summary: ${result.summary}`);
}

function log(msg) {
    document.getElementById('output').textContent += msg + '\\n';
}
</script>
</body>
</html>"""

    def get_npm_package(self) -> dict:
        return {
            "name": "@pdfmind/sdk",
            "version": "2026.6",
            "description": "PDFMind JavaScript SDK for PDF operations (free, MIT license)",
            "main": "dist/pdfmind-sdk.js",
            "module": "dist/pdfmind-sdk.esm.js",
            "types": "dist/pdfmind-sdk.d.ts",
            "files": ["dist"],
            "scripts": {
                "build": "rollup -c",
                "test": "jest",
                "lint": "eslint src/",
            },
            "dependencies": {},
            "devDependencies": {
                "rollup": "^3.0.0",
                "typescript": "^5.0.0",
                "jest": "^29.0.0",
            },
            "keywords": ["pdf", "pdfmind", "sdk", "api"],
            "license": "MIT",
        }

    def get_typescript_defs(self) -> str:
        return """export declare class PDFMind {
    constructor(config?: { baseUrl?: string; timeout?: number });
    health(): Promise<any>;
    documents: DocumentAPI;
    pages: PageAPI;
    elements: ElementAPI;
    ai: AIAPI;
    export: ExportAPI;
}
export declare class PDFMindError extends Error {
    statusCode: number;
    details: any;
}
export interface DocumentInfo {
    id: string;
    title: string;
    page_count: number;
    created_at: string;
}
export interface PageInfo {
    index: number;
    width: number;
    height: number;
    rotation: number;
}
export interface ElementInfo {
    id: string;
    type: string;
    content: string;
    x: number;
    y: number;
}
export declare class DocumentAPI {
    list(params?: any): Promise<any>;
    open(file: File | string): Promise<DocumentInfo>;
    get(documentId: string): Promise<DocumentInfo>;
    create(options?: any): Promise<DocumentInfo>;
    delete(documentId: string): Promise<void>;
    merge(documentIds: string[], outputName?: string): Promise<any>;
    split(documentId: string, options?: any): Promise<any>;
    compress(documentId: string, level?: string): Promise<any>;
    extractText(documentId: string, pageRange?: number[]): Promise<any>;
    download(documentId: string): Promise<Blob>;
}
export declare class PageAPI {
    list(documentId: string): Promise<PageInfo[]>;
    add(documentId: string, options?: any): Promise<any>;
    remove(documentId: string, pageIndex: number): Promise<void>;
    reorder(documentId: string, pageOrder: number[]): Promise<void>;
    rotate(documentId: string, pageIndex: number, angle?: number): Promise<void>;
}
export declare class ElementAPI {
    list(documentId: string, pageIndex: number): Promise<ElementInfo[]>;
    add(documentId: string, pageIndex: number, element: any): Promise<ElementInfo>;
    update(documentId: string, pageIndex: number, elementId: string, updates: any): Promise<void>;
    remove(documentId: string, pageIndex: number, elementId: string): Promise<void>;
}
export declare class AIAPI {
    summarize(documentId: string, options?: any): Promise<any>;
    ask(documentId: string, question: string): Promise<any>;
    redactSmart(documentId: string, types?: string[]): Promise<any>;
    translate(documentId: string, targetLang: string): Promise<any>;
}
export declare class ExportAPI {
    toFormat(documentId: string, format: string, options?: any): Promise<any>;
}"""
