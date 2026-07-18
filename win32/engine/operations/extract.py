"""Page extraction operations.

Extract pages to new PDFs, extract text content, embedded images,
and annotations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import fitz  # PyMuPDF


def extract_to_pdf(
    source: Union[str, Path, fitz.Document],
    pages: Sequence[int],
    output_path: Union[str, Path],
) -> Path:
    """Extract selected pages into a new PDF file."""
    doc = _open(source)
    out = fitz.open()
    for p in pages:
        if 0 <= p < len(doc):
            out.insert_pdf(doc, from_page=p, to_page=p)
    out.save(str(output_path))
    out.close()
    return Path(output_path)


def extract_text(
    source: Union[str, Path, fitz.Document],
    pages: Optional[Sequence[int]] = None,
    mode: str = "text",
) -> Dict[int, str]:
    """Extract text content from pages.

    Args:
        source: Input PDF.
        pages: Page indices; ``None`` = all pages.
        mode: ``"text"`` for plain text, ``"blocks"`` for structured blocks.

    Returns:
        Mapping of page index to extracted text.
    """
    doc = _open(source)
    targets = pages if pages is not None else range(len(doc))
    results: Dict[int, str] = {}
    for p in targets:
        if 0 <= p < len(doc):
            page = doc[p]
            if mode == "blocks":
                blocks = page.get_text("blocks")
                parts = []
                for b in blocks:
                    if b[6] == 0:
                        parts.append(b[4].strip())
                results[p] = "\n".join(parts)
            else:
                results[p] = page.get_text("text")
    return results


def extract_text_detailed(
    source: Union[str, Path, fitz.Document],
    page_index: int,
) -> Dict[str, Any]:
    """Extract detailed text information including positions, fonts, sizes."""
    doc = _open(source)
    page = doc[page_index]
    text_dict = page.get_text("dict")
    lines_info: List[Dict[str, Any]] = []
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans_data = []
            for span in line.get("spans", []):
                spans_data.append({
                    "text": span["text"],
                    "font": span["font"],
                    "size": span["size"],
                    "color": span["color"],
                    "bbox": list(span["bbox"]),
                    "flags": span.get("flags", 0),
                })
            lines_info.append({
                "bbox": list(line["bbox"]),
                "direction": line.get("dir", "ltr"),
                "spans": spans_data,
            })
    return {"page": page_index, "lines": lines_info}


def extract_images_from_page(
    source: Union[str, Path, fitz.Document],
    page_index: int,
    output_dir: Optional[Union[str, Path]] = None,
) -> List[Dict[str, Any]]:
    """Extract all images embedded in a page.

    Returns metadata for each image including xref, dimensions, and
    optionally saves the image to *output_dir*.
    """
    doc = _open(source)
    page = doc[page_index]
    images = page.get_images(full=True)
    results: List[Dict[str, Any]] = []

    out_dir = Path(output_dir) if output_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    for img_idx, img_info in enumerate(images):
        xref = img_info[0]
        smask = img_info[1]
        width = img_info[2]
        height = img_info[3]
        bpc = img_info[4]
        colorspace = img_info[5]

        base_image = doc.extract_image(xref)
        ext = base_image.get("ext", "png")
        img_bytes = base_image.get("image", b"")

        saved_path = None
        if out_dir and img_bytes:
            fname = f"page{page_index}_img{img_idx}.{ext}"
            save_to = out_dir / fname
            save_to.write_bytes(img_bytes)
            saved_path = str(save_to)

        results.append({
            "xref": xref,
            "smask": smask,
            "width": width,
            "height": height,
            "bpc": bpc,
            "colorspace": colorspace,
            "ext": ext,
            "size_bytes": len(img_bytes),
            "path": saved_path,
        })
    return results


def extract_annotations(
    source: Union[str, Path, fitz.Document],
    page_index: int,
) -> List[Dict[str, Any]]:
    """Extract annotation data from a page."""
    doc = _open(source)
    page = doc[page_index]
    annots = []
    annot = page.first_annot
    while annot:
        info: Dict[str, Any] = {
            "type": annot.type[1] if annot.type else "unknown",
            "rect": list(annot.rect),
            "content": annot.info.get("content", ""),
            "author": annot.info.get("title", ""),
            "subject": annot.info.get("subject", ""),
            "color": list(annot.colors.get("stroke", (0, 0, 0))),
            "flags": annot.flags,
            "name": annot.name or "",
        }
        if annot.type and annot.type[0] in (2, 8):
            info["ink_data"] = annot.get_ink()
        annots.append(info)
        annot = annot.next
    return annots


def extract_form_fields(
    source: Union[str, Path, fitz.Document],
) -> List[Dict[str, Any]]:
    """Extract form field information from all pages."""
    doc = _open(source)
    fields = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        widgets = page.widgets()
        if widgets:
            for w in widgets:
                fields.append({
                    "page": page_num,
                    "field_name": w.field_name,
                    "field_type": w.field_type_string,
                    "field_value": w.field_value,
                    "rect": list(w.rect),
                    "field_label": w.field_label or "",
                    "is_required": bool(w.field_flags & 2 ** 1),
                })
    return fields


def _open(src: Union[str, Path, fitz.Document]) -> fitz.Document:
    if isinstance(src, fitz.Document):
        return src
    return fitz.open(str(src))
