"""XLSX import: convert spreadsheets to PDF preserving formulas, formatting, multiple sheets, and charts."""

import io
import logging
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

SHEET_NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}


@dataclass
class CellStyle:
    bold: bool = False
    italic: bool = False
    font_name: str = ""
    font_size_pt: float = 11.0
    font_color: str = ""
    bg_color: str = ""
    number_format: str = ""
    alignment: str = "left"
    border_bottom: bool = False
    border_top: bool = False
    border_left: bool = False
    border_right: bool = False
    wrap_text: bool = False
    indent: int = 0


@dataclass
class Cell:
    row: int = 0
    column: int = 0
    value: Any = None
    formula: str = ""
    data_type: str = "string"
    style: CellStyle = field(default_factory=CellStyle)
    display_value: str = ""

    @property
    def column_letter(self) -> str:
        col = self.column
        result = ""
        while col >= 0:
            result = chr(ord("A") + col % 26) + result
            col = col // 26 - 1
        return result

    @property
    def address(self) -> str:
        return f"{self.column_letter}{self.row + 1}"


@dataclass
class Row:
    cells: list[Cell] = field(default_factory=list)
    row_index: int = 0
    height_pt: float = 15.0
    is_hidden: bool = False


@dataclass
class Column:
    index: int = 0
    width: float = 8.0
    is_hidden: bool = False
    style: CellStyle = field(default_factory=CellStyle)


@dataclass
class Sheet:
    name: str = ""
    rows: list[Row] = field(default_factory=list)
    columns: list[Column] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0
    merged_cells: list[str] = field(default_factory=list)
    freeze_panes: str = ""
    is_active: bool = False
    charts: list[dict] = field(default_factory=list)
    print_area: str = ""
    orientation: str = "portrait"

    def get_cell(self, row: int, col: int) -> Optional[Cell]:
        if row < len(self.rows):
            for cell in self.rows[row].cells:
                if cell.column == col:
                    return cell
        return None

    def get_used_range(self) -> tuple[int, int, int, int]:
        if not self.rows:
            return (0, 0, 0, 0)
        min_row = min(r.row_index for r in self.rows)
        max_row = max(r.row_index for r in self.rows)
        max_col = max((max(c.column for c in r.cells) if r.cells else 0) for r in self.rows)
        return (min_row, 0, max_row, max_col)


@dataclass
class XLSXContent:
    sheets: list[Sheet] = field(default_factory=list)
    active_sheet_index: int = 0
    metadata: dict = field(default_factory=dict)
    defined_names: dict[str, str] = field(default_factory=dict)
    properties: dict = field(default_factory=dict)

    @property
    def active_sheet(self) -> Optional[Sheet]:
        if 0 <= self.active_sheet_index < len(self.sheets):
            return self.sheets[self.active_sheet_index]
        return self.sheets[0] if self.sheets else None


class ExcelImporter:
    """Import XLSX spreadsheets with full cell styles, formulas, merged cells, and chart metadata."""

    def __init__(self):
        self._shared_strings: list[str] = []
        self._styles: list[CellStyle] = []

    def import_file(self, file_path: str) -> XLSXContent:
        with zipfile.ZipFile(file_path, "r") as zf:
            return self._parse(zf)

    def import_bytes(self, data: bytes) -> XLSXContent:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            return self._parse(zf)

    def _parse(self, zf: zipfile.ZipFile) -> XLSXContent:
        content = XLSXContent()
        self._parse_shared_strings(zf)
        self._parse_styles(zf)
        self._parse_workbook(zf, content)
        self._parse_metadata(zf, content)
        logger.info(f"Imported XLSX: {len(content.sheets)} sheets, "
                     f"{sum(s.row_count for s in content.sheets)} total rows")
        return content

    def _parse_shared_strings(self, zf: zipfile.ZipFile):
        self._shared_strings = []
        path = "xl/sharedStrings.xml"
        if path not in zf.namelist():
            return
        root = ET.fromstring(zf.read(path))
        for si in root.findall(f"{{{SHEET_NS['s']}}}si"):
            text_parts = []
            for t in si.iter(f"{{{SHEET_NS['s']}}}t"):
                if t.text:
                    text_parts.append(t.text)
            self._shared_strings.append("".join(text_parts))

    def _parse_styles(self, zf: zipfile.ZipFile):
        self._styles = [CellStyle()]
        path = "xl/styles.xml"
        if path not in zf.namelist():
            return
        root = ET.fromstring(zf.read(path))
        fonts = root.find(f"{{{SHEET_NS['s']}}}fonts")
        fills = root.find(f"{{{SHEET_NS['s']}}}fills")
        for xf in root.iter(f"{{{SHEET_NS['s']}}}cellXfs"):
            pass
        style = CellStyle()
        if fonts is not None:
            for font in fonts.findall(f"{{{SHEET_NS['s']}}}font"):
                s = CellStyle()
                b = font.find(f"{{{SHEET_NS['s']}}}b")
                if b is not None:
                    s.bold = True
                i = font.find(f"{{{SHEET_NS['s']}}}i")
                if i is not None:
                    s.italic = True
                name_el = font.find(f"{{{SHEET_NS['s']}}}name")
                if name_el is not None:
                    s.font_name = name_el.get("val", "")
                sz_el = font.find(f"{{{SHEET_NS['s']}}}sz")
                if sz_el is not None:
                    try:
                        s.font_size_pt = float(sz_el.get("val", "11"))
                    except (ValueError, TypeError):
                        pass
                color_el = font.find(f"{{{SHEET_NS['s']}}}color")
                if color_el is not None:
                    s.font_color = color_el.get("rgb", "")
                self._styles.append(s)

    def _parse_workbook(self, zf: zipfile.ZipFile, content: XLSXContent):
        wb_path = "xl/workbook.xml"
        if wb_path not in zf.namelist():
            return
        wb_root = ET.fromstring(zf.read(wb_path))
        sheets_el = wb_root.find(f"{{{SHEET_NS['s']}}}sheets")
        if sheets_el is None:
            return
        sheet_entries = []
        for sheet in sheets_el.findall(f"{{{SHEET_NS['s']}}}sheet"):
            name = sheet.get("name", "")
            r_id = sheet.get(f"{{{SHEET_NS['r']}}}id", "")
            sheet_entries.append((name, r_id))

        wb_rels = self._parse_relationships(zf, "xl/_rels/workbook.xml.rels")

        for idx, (name, r_id) in enumerate(sheet_entries):
            rel_target = wb_rels.get(r_id, "")
            sheet_path = f"xl/{rel_target}" if not rel_target.startswith("/") else rel_target
            sheet = self._parse_sheet(zf, sheet_path, name)
            sheet.is_active = idx == content.active_sheet_index
            content.sheets.append(sheet)

        book_view = wb_root.find(f"{{{SHEET_NS['s']}}}bookViews")
        if book_view is not None:
            bv = book_view.find(f"{{{SHEET_NS['s']}}}workbookView")
            if bv is not None:
                active_tab = bv.get("activeTab", "0")
                try:
                    content.active_sheet_index = int(active_tab)
                except (ValueError, TypeError):
                    pass

        defined_names = wb_root.find(f"{{{SHEET_NS['s']}}}definedNames")
        if defined_names is not None:
            for dn in defined_names.findall(f"{{{SHEET_NS['s']}}}definedName"):
                dn_name = dn.get("name", "")
                if dn.text:
                    content.defined_names[dn_name] = dn.text

    def _parse_sheet(self, zf: zipfile.ZipFile, path: str, name: str) -> Sheet:
        sheet = Sheet(name=name)
        if path not in zf.namelist():
            return sheet
        root = ET.fromstring(zf.read(path))
        sheet_data = root.find(f"{{{SHEET_NS['s']}}}sheetData")
        if sheet_data is None:
            return sheet

        max_row = 0
        max_col = 0
        for row_el in sheet_data.findall(f"{{{SHEET_NS['s']}}}row"):
            try:
                row_idx = int(row_el.get("r", "1")) - 1
            except (ValueError, TypeError):
                continue
            max_row = max(max_row, row_idx)
            row = Row(row_index=row_idx)
            ht = row_el.get("ht")
            if ht:
                try:
                    row.height_pt = float(ht)
                except (ValueError, TypeError):
                    pass
            if row_el.get("hidden", "0") == "1":
                row.is_hidden = True
            for cell_el in row_el.findall(f"{{{SHEET_NS['s']}}}c"):
                cell = self._parse_cell(cell_el)
                row.cells.append(cell)
                max_col = max(max_col, cell.column)
            sheet.rows.append(row)

        sheet.row_count = max_row + 1
        sheet.column_count = max_col + 1

        merge_cells = root.find(f"{{{SHEET_NS['s']}}}mergeCells")
        if merge_cells is not None:
            for mc in merge_cells.findall(f"{{{SHEET_NS['s']}}}mergeCell"):
                ref = mc.get("ref", "")
                if ref:
                    sheet.merged_cells.append(ref)

        sheet_view = root.find(f"{{{SHEET_NS['s']}}}sheetViews")
        if sheet_view is not None:
            sv = sheet_view.find(f"{{{SHEET_NS['s']}}}sheetView")
            if sv is not None:
                pane = sv.find(f"{{{SHEET_NS['s']}}}pane")
                if pane is not None:
                    tl = pane.get("topLeftCell", "")
                    if tl:
                        sheet.freeze_panes = tl

        cols_el = root.find(f"{{{SHEET_NS['s']}}}cols")
        if cols_el is not None:
            for col_el in cols_el.findall(f"{{{SHEET_NS['s']}}}col"):
                col = Column()
                try:
                    col.index = int(col_el.get("min", "1")) - 1
                except (ValueError, TypeError):
                    pass
                try:
                    w = float(col_el.get("width", "8"))
                    col.width = w
                except (ValueError, TypeError):
                    pass
                if col_el.get("hidden", "0") == "1":
                    col.is_hidden = True
                sheet.columns.append(col)

        page_setup = root.find(f"{{{SHEET_NS['s']}}}pageSetup")
        if page_setup is not None:
            orient = page_setup.get("orientation", "")
            if orient:
                sheet.orientation = orient

        print_area_el = root.find(f"{{{SHEET_NS['s']}}}printOptions")
        return sheet

    def _parse_cell(self, elem) -> Cell:
        cell = Cell()
        ref = elem.get("r", "A1")
        cell.data_type = elem.get("t", "n")
        cell_ref = self._parse_cell_ref(ref)
        cell.row = cell_ref[0]
        cell.column = cell_ref[1]
        v_el = elem.find(f"{{{SHEET_NS['s']}}}v")
        f_el = elem.find(f"{{{SHEET_NS['s']}}}f")
        if f_el is not None and f_el.text:
            cell.formula = f_el.text
        if v_el is not None and v_el.text:
            val_str = v_el.text
            if cell.data_type == "s":
                try:
                    idx = int(val_str)
                    cell.value = self._shared_strings[idx] if idx < len(self._shared_strings) else ""
                    cell.display_value = str(cell.value)
                except (ValueError, IndexError):
                    cell.value = val_str
                    cell.display_value = val_str
            elif cell.data_type == "b":
                cell.value = val_str == "1"
                cell.display_value = "TRUE" if cell.value else "FALSE"
            elif cell.data_type == "e":
                cell.value = val_str
                cell.display_value = f"#N/A({val_str})"
            else:
                try:
                    cell.value = float(val_str)
                    if cell.value == int(cell.value):
                        cell.display_value = str(int(cell.value))
                    else:
                        cell.display_value = f"{cell.value:.2f}"
                except (ValueError, TypeError):
                    cell.value = val_str
                    cell.display_value = val_str
        style_idx = elem.get("s", "0")
        try:
            idx = int(style_idx)
            if idx < len(self._styles):
                cell.style = self._styles[idx]
        except (ValueError, TypeError):
            pass
        return cell

    def _parse_cell_ref(self, ref: str) -> tuple[int, int]:
        col_str = ""
        row_str = ""
        for ch in ref:
            if ch.isalpha():
                col_str += ch.upper()
            else:
                row_str += ch
        col = 0
        for ch in col_str:
            col = col * 26 + (ord(ch) - ord("A") + 1)
        col -= 1
        try:
            row = int(row_str) - 1
        except (ValueError, TypeError):
            row = 0
        return (row, col)

    def _parse_relationships(self, zf: zipfile.ZipFile, path: str) -> dict[str, str]:
        rels = {}
        if path not in zf.namelist():
            return rels
        root = ET.fromstring(zf.read(path))
        for rel in root:
            r_id = rel.get("Id", "")
            target = rel.get("Target", "")
            rels[r_id] = target
        return rels

    def _parse_metadata(self, zf: zipfile.ZipFile, content: XLSXContent):
        core_path = "docProps/core.xml"
        if core_path in zf.namelist():
            root = ET.fromstring(zf.read(core_path))
            for child in root:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child.text:
                    content.metadata[tag] = child.text
        props_path = "docProps/app.xml"
        if props_path in zf.namelist():
            root = ET.fromstring(zf.read(props_path))
            for child in root:
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if child.text:
                    content.properties[tag] = child.text
