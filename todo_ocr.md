# OCR Client Work Log

## Completed
- [x] Added local OCR backend scaffolding (Tesseract) in `ocr_utils.py`
- [x] Determined Tesseract engine is NOT installed (no `tesseract.exe`)
- [x] Selected Google Cloud Vision OCR client mode (no local executables)
- [x] Added Google Cloud Vision client module `ocr_google_cloud.py`

## Pending
- [ ] Add OCR UI/menus: OCR current page + OCR all pages
- [ ] Render PDF page at high DPI for OCR
- [ ] Convert OCR bounding boxes to editor coordinates and create text elements
- [ ] Thread OCR to avoid UI freeze
- [ ] Update requirements.txt with OCR dependencies (google-cloud-vision)
- [ ] Wire OCR into save/preview/undo/redo/selection/page navigation
- [ ] Smoke test on tmp_test_input.pdf / tmp_preview_test.pdf
- [ ] Iterate until stable

