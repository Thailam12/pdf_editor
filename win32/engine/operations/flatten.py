"""Flatten operations.

Flatten annotations, form fields, transparency, and layers into
static page content.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union

import fitz  # PyMuPDF


def flatten_annotations(
    doc: fitz.Document,
    pages: Optional[Sequence[int]] = None,
    keep_text: bool = True,
) -> int:
    """Flatten annotations into page content so they become part of the
    rendered page rather than overlay objects.

    Returns the total number of annotations flattened.
    """
    targets = pages if pages is not None else range(len(doc))
    total_flattened = 0
    for p in targets:
        if p < 0 or p >= len(doc):
            continue
        page = doc[p]
        annot = page.first_annot
        count = 0
        while annot:
            next_annot = annot.next
            annot_type = annot.type[0] if annot.type else -1
            should_flatten = annot_type in (0, 1, 2, 5, 6, 7, 8, 9, 10, 12, 15)
            if should_flatten:
                rect = annot.rect
                content = annot.info.get("content", "")
                if content and keep_text:
                    page.insert_textbox(
                        rect, content,
                        fontsize=annot.info.get("fontSize", 10),
                        color=annot.colors.get("stroke", (0, 0, 0)),
                    )
                elif annot_type in (2, 8):
                    _flatten_ink(page, annot)
                elif annot_type == 0:
                    _flatten_stamp(page, annot)
                page.delete_annot(annot)
                count += 1
            annot = next_annot
        total_flattened += count
    return total_flattened


def flatten_form_fields(
    doc: fitz.Document,
    pages: Optional[Sequence[int]] = None,
) -> int:
    """Flatten form fields into static page content.

    Returns the number of fields flattened.
    """
    targets = pages if pages is not None else range(len(doc))
    total = 0
    for p in targets:
        if p < 0 or p >= len(doc):
            continue
        page = doc[p]
        widgets = list(page.widgets() or [])
        for w in widgets:
            rect = fitz.Rect(w.rect)
            value = w.field_value or ""
            field_type = w.field_type_string
            if field_type == "checkBox":
                if value:
                    page.draw_rect(rect, color=(0, 0, 0), width=0.5)
                    if value.lower() in ("yes", "true", "on", "1", "checked"):
                        page.draw_line(
                            fitz.Point(rect.x0 + 3, (rect.y0 + rect.y1) / 2),
                            fitz.Point((rect.x0 + rect.x1) / 2, rect.y1 - 3),
                            color=(0, 0, 0), width=1.5,
                        )
                        page.draw_line(
                            fitz.Point((rect.x0 + rect.x1) / 2, rect.y1 - 3),
                            fitz.Point(rect.x1 - 3, rect.y0 + 3),
                            color=(0, 0, 0), width=1.5,
                        )
            elif field_type == "button":
                page.insert_textbox(
                    rect, value, fontsize=9,
                    color=(0, 0, 0), align=fitz.TEXT_ALIGN_CENTER,
                )
            else:
                page.insert_textbox(
                    rect, value, fontsize=10, color=(0, 0, 0),
                )
            total += 1
    return total


def flatten_transparency(
    doc: fitz.Document,
    pages: Optional[Sequence[int]] = None,
) -> int:
    """Flatten transparency groups on pages by rendering and reinserting.

    Returns the number of pages processed.
    """
    targets = pages if pages is not None else range(len(doc))
    processed = 0
    for p in targets:
        if p < 0 or p >= len(doc):
            continue
        page = doc[p]
        xobjects = page.get_xobjects()
        if not xobjects:
            continue
        has_transparency = False
        for xobj in xobjects:
            xref = xobj[0]
            obj_dict = doc.xref_object(xref, compressed=False)
            if "/SMask" in obj_dict or "/Group" in obj_dict:
                has_transparency = True
                break
        if has_transparency:
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            rect = page.rect
            page.clean_contents()
            page.insert_image(rect, pixmap=pix)
            processed += 1
    return processed


def merge_visible_layers(
    doc: fitz.Document,
    pages: Optional[Sequence[int]] = None,
) -> int:
    """Merge all visible annotation layers into the base page content.

    Returns the number of pages processed.
    """
    targets = pages if pages is not None else range(len(doc))
    count = 0
    for p in targets:
        if p < 0 or p >= len(doc):
            continue
        page = doc[p]
        annot_list = []
        annot = page.first_annot
        while annot:
            annot_list.append(annot)
            annot = annot.next
        if not annot_list:
            continue
        mat = fitz.Matrix(1, 1)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        page.clean_contents()
        page.insert_image(page.rect, pixmap=pix)
        count += 1
    return count
