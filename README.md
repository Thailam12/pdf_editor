# PDFMind AI — Ultimate PDF Editor

**Version v2026.6** | **100% Free & Open Source** | MIT License | No API Keys | No Subscriptions

A Word-like super PDF editor with a 100M-parameter local AI model, built across three platforms: native Win32 (Python/tkinter), UWP (C++/WinRT), and Web (Flask + React). Release v2026.6 focuses on better reliability, clearer OCR feedback, faster health reporting, stronger cross-platform readiness, and a cleaner deprecation path for legacy PDF operations.

## Release Highlights

- Improved OCR feedback and diagnostics for scanned documents
- Faster startup and more informative health checks
- Better cloud-sync readiness and web responsiveness
- Updated version metadata across Win32, UWP, and Web surfaces

---

## Stats

| Metric | Value |
|--------|-------|
| **Current Release** | v2026.6 |
| **Total Source Files** | 295 |
| **Total Lines of Code** | **52,377** |
| **AI Model Parameters** | 100.4M |
| **Platforms** | 3 (Win32, UWP, Web) |
| **License** | MIT (Free forever) |

### Lines of Code by Module

| Module | Files | LOC | Description |
|--------|-------|-----|-------------|
| `engine/` | 31 | 8,927 | PDF parser, renderer, elements, operations, search, I/O |
| `uwp/` | 82 | 7,114 | WinUI3 C++ desktop app (Fluent Design 2) |
| `services/` | 50 | 7,666 | AI inference, PDF/A, accessibility, redaction, Bates, TTS, etc. |
| `integrations/` | 27 | 6,181 | Cloud (Drive, Dropbox, Box), Office, CLI, SDK, MCP Server |
| `shipping/` | 27 | 4,451 | Themes, templates, performance, packaging, Microsoft Store |
| `enterprise/` | 17 | 2,555 | Compliance (HIPAA, GDPR, PDF/A, PDF/UA), encryption, Azure AD |
| `ai_model/` | 25 | 3,833 | PDFMind 100M transformer, QLoRA training, ONNX/GGUF export |
| `win32/` | 3 | 1,399 | Native Python/tkinter PDF editor |
| `web/` | 14 | 220 | Flask REST API + React frontend |

---

## Quick Start

### Win32 (Native Desktop)
```bash
pip install -r win32/requirements.txt
python win32/main.py
# Local-only mode is the default; remote integrations require explicit opt-in.
python win32/main.py --local
```

### UWP (WinUI3 Desktop)
```
Open uwp/PDFEditor.sln in Visual Studio 2022 → Build & Run
```

### Web (Flask + React)
```bash
pip install -r win32/requirements.txt
python web/run_web.py
# Open http://127.0.0.1:5000
```

The web runner requires the Web Backend packages from `win32/requirements.txt`,
including `flask` and `flask-cors`. If your active Python environment reports
these imports as missing, install the requirements into that same interpreter.

### Local-First Operation

PDFMind processes documents locally by default. Local AI, OCR, editing, search,
compression, encryption, and batch operations do not require an account, API
key, or internet connection. The Win32 app exposes `--local` explicitly and
requires `--allow-network` to enable optional cloud or remote AI integrations.

The project remains free and open source under the MIT License. Existing author
and project credits are retained in this README and the application metadata.

### Deprecated Legacy Commands

The following PDF commands remain available for compatibility, but now emit a
clear warning and should be treated as legacy:

- `encrypt`
- `decrypt`
- `sign`
- `watermark`

They still run for existing workflows, but they are no longer the recommended
path for future automation. The `validate` command is the supported local
replacement for routine PDF integrity checks.

### Local Productivity Features

```bash
# Save and list local PDF snapshots
python -m win32.integrations.developer.cli history create document.pdf
python -m win32.integrations.developer.cli history list document.pdf

# Extract text without uploading the document
python -m win32.integrations.developer.cli extract-text document.pdf -o document.txt

# Verify file integrity locally
python -m win32.integrations.developer.cli checksum document.pdf

# Inspect several PDFs in one local operation
python -m win32.integrations.developer.cli batch-info *.pdf

# Check local dependencies and runtime capabilities
python -m win32.integrations.developer.cli diagnostics

# Validate a PDF can be opened locally and report its page count
python -m win32.integrations.developer.cli validate document.pdf

# Request machine-readable validation output
python -m win32.integrations.developer.cli --json validate document.pdf
```

History snapshots are stored under `~/.pdfmind/history` and include a SHA-256
digest plus creation timestamp. No network request is needed for any of these
commands. The `validate` command opens the file locally with PyMuPDF and returns
a non-zero exit code for missing or unreadable PDFs.

### Docker
```bash
docker-compose up --build
```

---

## Project Structure

```
pdf_editor/
├── ai_model/               # PDFMind 100M — 100.4M param transformer
│   ├── config.py           # Model config (SwiGLU + RoPE + RMSNorm + GQA)
│   ├── model.py            # Full transformer implementation
│   ├── tokenizer.py        # BPE tokenizer with PDF-aware preprocessing
│   ├── dataset.py          # Training datasets (text, instruction, distillation)
│   ├── train_qlora.py      # QLoRA fine-tuning (NF4 + BF16 LoRA adapters)
│   ├── train_distill.py    # Knowledge distillation from 7B teacher
│   ├── train_pretrain.py   # Pretraining with cosine warmup
│   ├── inference.py        # Unified inference (PyTorch/ONNX/GGUF backends)
│   ├── inference_vulkan.py # Vulkan iGPU inference via llama.cpp
│   ├── export_onnx.py      # ONNX FP32 + INT8 quantized export
│   ├── export_gguf.py      # GGUF Q4/Q8 export
│   └── tasks/              # 8 AI task modules
│       ├── pdf_summarizer.py
│       ├── pdf_question_answerer.py
│       ├── pii_detector.py         # 40+ PII entity types
│       ├── ocr_corrector.py
│       ├── form_extractor.py
│       ├── document_comparator.py
│       ├── pdf_translator.py       # 100+ languages
│       └── proofreader.py
│
├── engine/                 # Core PDF Engine (PyMuPDF-based)
│   ├── parser/             # PDF parsing
│   │   ├── pdf_parser.py   # Full PDF spec parser
│   │   ├── object_model.py # 25+ dataclasses (Document, Page, etc.)
│   │   ├── content_stream.py # Content stream interpreter
│   │   └── font_handler.py # Font parsing (Type0/1/TrueType/CID/Type3)
│   ├── renderer/           # PDF rendering
│   │   ├── software_renderer.py # Software rasterizer
│   │   ├── text_renderer.py     # Text rendering with bidi
│   │   └── image_loader.py      # Image loading with format detection
│   ├── elements/           # PDF elements
│   │   ├── base.py         # Base element, AffineTransform
│   │   ├── text.py         # Text elements with word wrap
│   │   ├── image.py        # Image elements (9 filters)
│   │   └── vector.py       # Vector shapes (12 types)
│   ├── operations/         # Page operations
│   │   ├── merge.py        # Merge multiple PDFs
│   │   ├── split.py        # Split by page/range/bookmarks
│   │   ├── rotate.py       # Rotate pages
│   │   ├── crop.py         # Crop with all 5 PDF boxes
│   │   ├── reorder.py      # Reorder pages
│   │   ├── extract.py      # Extract to PDF/text/images
│   │   └── flatten.py      # Flatten annotations
│   ├── io/                 # File I/O
│   │   ├── reader.py       # PDF reader (lazy, password, repair, mmap)
│   │   ├── writer.py       # PDF writer (create/rewrite, font embedding)
│   │   └── incremental.py  # Incremental save with change tracking
│   └── search/             # Search
│       ├── text_search.py  # Indexed text search
│       ├── regex_search.py # Regex search with pattern library
│       └── semantic_search.py # AI semantic search (sentence-transformers)
│
├── services/               # Service Layer
│   ├── ai/                 # AI inference service
│   ├── pdf_engine/         # PDF processing service
│   ├── cloud_services/     # Cloud integrations
│   ├── enterprise_services/ # Enterprise features
│   ├── integrations_services/ # Third-party integrations
│   └── advanced/           # Advanced features
│       ├── advanced_pdfa_service.py          # PDF/A compliance (all 9 levels)
│       ├── advanced_accessibility_service.py # PDF/UA + WCAG 2.1 AA
│       ├── advanced_redaction_service.py     # AI-powered PII/PHI redaction
│       ├── advanced_bates_service.py         # Bates numbering
│       ├── advanced_tts_service.py           # Text-to-speech
│       ├── advanced_measurement_service.py   # Measurement tools
│       ├── advanced_compare_service.py       # Document comparison
│       ├── advanced_compress_service.py      # PDF compression
│       ├── advanced_spellcheck_service.py    # Multi-language spell check
│       └── advanced_print_service.py         # Advanced printing
│
├── enterprise/             # Enterprise & Compliance
│   ├── compliance/         # Compliance checkers
│   │   ├── pdfa_validator.py   # PDF/A validation
│   │   ├── pdfua_checker.py    # PDF/UA accessibility
│   │   ├── hipaa_checker.py    # HIPAA compliance
│   │   └── gdpr_checker.py     # GDPR compliance
│   ├── security/           # Security
│   │   ├── encryption.py       # AES-256 encryption
│   │   ├── digital_signatures.py # PAdES digital signatures
│   │   └── certificate_store.py  # Certificate management
│   └── admin/              # Administration
│       ├── admin_console.py    # User management + audit logging
│       └── license_manager.py  # Feature flags (all features free)
│
├── integrations/           # Third-party Integrations
│   ├── cloud/              # Cloud storage
│   │   ├── google_drive.py
│   │   ├── dropbox.py
│   │   ├── box.py
│   │   └── webdav.py
│   ├── office/             # Office documents
│   │   ├── word_import.py      # DOCX import
│   │   ├── excel_import.py     # XLSX import
│   │   ├── powerpoint_import.py # PPTX import
│   │   └── outlook.py          # Outlook integration
│   ├── developer/          # Developer tools
│   │   ├── rest_api.py         # REST API (OpenAPI 3.0)
│   │   ├── cli.py              # Command-line interface
│   │   ├── sdk_python.py       # Python SDK
│   │   ├── sdk_javascript.py   # JavaScript SDK
│   │   └── mcp_server.py       # MCP Server for AI agents
│   ├── printing/           # Print management
│   │   ├── print_manager.py
│   │   ├── pdf_printer.py
│   │   └── plotter.py
│   └── import_export/      # Format converters
│       ├── epub.py, djvu.py, tiff.py, svg.py, markdown.py
│
├── shipping/               # Ship, Polish & Sell
│   ├── ui_polish/          # UI polish
│   │   ├── animations.py       # 20+ animation presets
│   │   ├── onboarding.py       # First-run wizard
│   │   ├── tooltips.py         # Contextual help
│   │   ├── tutorial.py         # Interactive tutorials
│   │   ├── templates_gallery.py # 50+ document templates
│   │   └── theme_engine.py     # 10 themes (Catppuccin, Dracula, Nord, etc.)
│   ├── performance/        # Performance optimization
│   │   ├── lazy_loading.py     # Lazy page loading
│   │   ├── memory_manager.py   # Smart memory management
│   │   ├── cache_system.py     # Multi-level caching
│   │   ├── parallel_render.py  # Multi-threaded rendering
│   │   └── startup_optimize.py # < 2s cold start
│   ├── packaging/          # Distribution
│   │   ├── installer_win.py    # MSI/MSIX installer
│   │   ├── portable.py         # Portable USB version
│   │   └── auto_update.py      # Delta auto-updater
│   ├── testing/            # Testing
│   │   ├── test_pdf_compat.py  # 1000+ PDF compatibility suite
│   │   ├── test_performance.py # Performance benchmarks
│   │   ├── test_security.py    # Security audit (30+ tests)
│   │   └── test_accessibility.py # WCAG 2.1 AA testing
│   └── microsoft_ready/    # Microsoft acquisition
│       ├── store_listing.py    # Microsoft Store listing
│       ├── pricing_tier.py     # All features free (MIT license)
│       └── pitch_deck.py       # $45.7B TAM acquisition pitch
│
├── win32/                  # Win32 Native App (Python/tkinter)
│   ├── main.py             # Entry point
│   ├── editor.py           # Main editor class
│   └── pdf_utils.py        # PDF utilities
│
├── uwp/                    # UWP App (C++/WinRT + WinUI3)
│   ├── PDFEditor.sln       # Visual Studio solution
│   ├── src/                # C++ source files
│   │   ├── App.xaml[.cpp]  # Application class
│   │   ├── MainWindow.xaml[.cpp] # Main window
│   │   ├── Controls/       # Custom controls
│   │   ├── Pages/          # XAML pages
│   │   ├── Services/       # Background services
│   │   └── ViewModels/     # MVVM view models
│   └── Package.appxmanifest
│
├── web/                    # Web App (Flask + React)
│   ├── run_web.py          # Entry point
│   ├── api/                # Flask REST API
│   │   ├── app.py          # App factory
│   │   └── routes/         # API endpoints
│   ├── services/           # Business logic
│   ├── utils/              # Utilities
│   └── frontend/           # React frontend
│       ├── package.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       └── src/            # React components
│
├── data/                   # Training data & datasets
├── models/                 # Pre-trained models
├── tests/                  # Test suite
├── tools/                  # Utility scripts
├── ui/                     # Shared UI components
├── static/                 # Static assets
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker build
├── docker-compose.yml      # Docker Compose
├── main.py                 # Main entry point
└── README.md               # This file
```

---

## Features

### Release 2.1 Highlights
- **OCR improvements** — clearer status messages and better diagnostics while processing scanned pages
- **Health visibility** — more informative health endpoints and startup feedback
- **Web responsiveness** — faster search and smoother API interactions
- **Cross-platform polish** — consistent versioning and release messaging across Win32, UWP, and Web

### AI-Powered (PDFMind 100M)
- **PDF Summarization** — Extractive summary with TF-IDF scoring
- **Question Answering** — Ask questions about PDF content with confidence scoring
- **PII Detection** — 40+ entity types (names, SSN, phone, email, etc.)
- **OCR Correction** — Fix OCR errors with rule-based + model correction
- **Form Extraction** — Detect and extract form fields
- **Document Comparison** — Visual diff with similarity scoring
- **Translation** — 100+ languages via local model
- **Proofreading** — Grammar, style, and readability analysis

### PDF Operations
- Merge, split, rotate, crop, reorder, extract, flatten
- Page thumbnails, bookmarks, annotations, form fields
- Text/regex/semantic search across documents
- Incremental save with change tracking
- Password protection and encryption

### Advanced Features
- PDF/A compliance (all 9 levels)
- PDF/UA accessibility checking
- Bates numbering for legal documents
- Smart redaction (AI-powered PII/PHI detection)
- Text-to-speech for accessibility
- Measurement tools (distance, area, angle)
- Document comparison (visual diff)
- Multi-level PDF compression
- Spell checking (30+ languages)

### Enterprise
- HIPAA compliance checking
- GDPR compliance checking
- AES-256 encryption
- PAdES digital signatures
- Azure AD SSO
- SharePoint/OneDrive integration
- User management + audit logging

### Integrations
- Google Drive, Dropbox, Box, WebDAV
- DOCX, XLSX, PPTX import
- REST API (OpenAPI 3.0)
- Python/JavaScript SDKs
- CLI tool
- MCP Server for AI agents

### UI
- Catppuccin Mocha dark theme (default)
- 10 theme options (Dracula, Nord, Solarized, etc.)
- 50+ document templates
- Interactive tutorials
- Keyboard shortcuts for everything
- Tabbed multi-document interface

---

## Keyboard Shortcuts

| Shortcut | Action | Shortcut | Action |
|----------|--------|----------|--------|
| Ctrl+O | Open PDF | Ctrl+Shift+M | Merge PDFs |
| Ctrl+S | Save PDF | Ctrl+Shift+R | Rotate Page |
| Ctrl+Shift+S | Save As | Ctrl+Shift+C | Compress |
| Ctrl+P | Print | Ctrl+Shift+F | Find & Replace |
| Ctrl+Z | Undo | Ctrl++ | Zoom In |
| Ctrl+Y | Redo | Ctrl+- | Zoom Out |
| Ctrl+C | Copy | Ctrl+0 | Reset Zoom |
| Ctrl+V | Paste | Ctrl+1 | Fit Width |
| Ctrl+A | Select All | F1 | Help |
| Delete | Delete Selected | F5 | Refresh |

---

## AI Model (PDFMind 100M)

### Architecture
- **Parameters**: 100.4M
- **Layers**: 24
- **Hidden dim**: 512
- **Attention**: 8 query heads / 2 KV heads (Grouped Query Attention)
- **Context**: 2,048 tokens
- **Vocab**: 32,000
- **Activations**: SwiGLU
- **Positional**: RoPE (Rotary Position Embeddings)
- **Normalization**: RMSNorm

### Training
- **QLoRA**: 4-bit NF4 quantized base + BF16 LoRA adapters (rank 16, alpha 32)
- **Knowledge Distillation**: From 7B teacher models
- **Datasets**: Synthetic PII data, document comprehension, form understanding

### Inference
- **Backends**: PyTorch, ONNX Runtime, llama.cpp (GGUF)
- **Quantization**: INT8 (ONNX) or Q4_K_M (GGUF, ~55MB)
- **iGPU**: Vulkan backend via llama.cpp (300-500 tok/s on Intel Iris Xe)
- **CPU**: 100-200 tok/s

### Export
```bash
# Export to ONNX INT8
python -m ai_model.export_onnx --output models/pdfmind_100m_int8.onnx

# Export to GGUF Q4
python -m ai_model.export_gguf --output models/pdfmind_100m_q4.gguf

# Full training pipeline
python -m ai_model.scripts.train_full --data data/

# Deploy with llama.cpp + Vulkan
python -m ai_model.scripts.deploy --gguf models/pdfmind_100m_q4.gguf
```

---

## Platform Details

### Win32 (Python/tkinter)
- **File**: `win32/main.py`
- **Dependencies**: PyMuPDF, reportlab, Pillow
- **Theme**: Catppuccin Mocha
- **Features**: Full PDF editing, AI assistant, all tools

### UWP (C++/WinRT + WinUI3)
- **File**: `uwp/PDFEditor.sln`
- **Dependencies**: Windows App SDK, Direct2D, DWrite
- **Theme**: Fluent Design 2 (Mica Alt)
- **Features**: Native Windows experience, 200+ ribbon tools

### Web (Flask + React)
- **File**: `web/run_web.py`
- **Dependencies**: Flask, React, MUI
- **Theme**: Catppuccin Mocha (custom)
- **Features**: 80+ API endpoints, real-time AI chat, side-by-side comparison

---

## License

MIT License — 100% free and open source. No API keys, no subscriptions, no hidden costs.

## Author

PDFMind AI — Built to surpass Adobe Acrobat and Foxit. Microsoft acquisition candidate ($45.7B TAM).
