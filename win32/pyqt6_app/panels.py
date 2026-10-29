# -*- coding: utf-8 -*-
"""PyQt6 dock panels: page thumbnails, layer list, property editor."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import (
    QListWidget, QListWidgetItem, QWidget, QFormLayout, QLineEdit,
    QSpinBox, QPushButton, QLabel, QVBoxLayout, QColorDialog,
    QHBoxLayout,
)

from win32.pyqt6_app.render import render_page


class PageList(QListWidget):
    page_selected = pyqtSignal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QPixmap(90, 120).size())
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSpacing(8)
        self.currentRowChanged.connect(self._on_row)

    def _on_row(self, row):
        if row >= 0:
            self.page_selected.emit(row)

    def reload_pages(self):
        self.blockSignals(True)
        self.clear()
        if self.controller.has_document:
            thumb_scale = 90.0 / max(1.0, self.controller.page(0).rect.width)
            for i in range(self.controller.total_pages):
                page = self.controller.page(i)
                pix = render_page(page, max(0.1, thumb_scale))
                item = QListWidgetItem(QIcon(pix), f"Page {i + 1}")
                self.addItem(item)
            self.setCurrentRow(self.controller.current_page)
        self.blockSignals(False)

    def set_current(self, index):
        if 0 <= index < self.count():
            self.blockSignals(True)
            self.setCurrentRow(index)
            self.blockSignals(False)


class LayersPanel(QListWidget):
    layer_selected = pyqtSignal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._index_map = []
        self.currentRowChanged.connect(self._on_row)

    def _on_row(self, row):
        if 0 <= row < len(self._index_map):
            self.layer_selected.emit(self._index_map[row])

    def reload(self):
        self.blockSignals(True)
        self.clear()
        self._index_map = []
        for idx, elem in self.controller.elements_on_current_page():
            name = getattr(elem, "name", "") or elem.type_name
            label = f"{elem.type_name}: {name}" if name else elem.type_name
            self.addItem(QListWidgetItem(label))
            self._index_map.append(idx)
        self.blockSignals(False)

    def select_element(self, index):
        if index in self._index_map:
            row = self._index_map.index(index)
            self.blockSignals(True)
            self.setCurrentRow(row)
            self.blockSignals(False)


class PropertiesPanel(QWidget):
    element_edited = pyqtSignal()

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        layout = QVBoxLayout(self)
        self._title = QLabel("No selection")
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        self.x_spin.setRange(-100000, 100000)
        self.y_spin.setRange(-100000, 100000)
        self.text_edit = QLineEdit()
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 400)
        self.color_row = QHBoxLayout()
        self.color_edit = QLineEdit()
        self.color_btn = QPushButton("…")
        self.color_btn.setFixedWidth(28)
        self.color_btn.clicked.connect(self._pick_color)
        self.color_row.addWidget(self.color_edit)
        self.color_row.addWidget(self.color_btn)

        form.addRow("Name", self.name_edit)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Text", self.text_edit)
        form.addRow("Font size", self.size_spin)
        form.addRow("Color", self.color_row)
        layout.addWidget(self._title)
        layout.addLayout(form)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        layout.addWidget(apply_btn)
        layout.addStretch(1)

    def show_element(self, index):
        elem = self.controller.selected_element() if index is not None else None
        if elem is None:
            self._title.setText("No selection")
            for w in (self.name_edit, self.x_spin, self.y_spin,
                      self.text_edit, self.size_spin, self.color_edit):
                w.setEnabled(False)
            return
        for w in (self.name_edit, self.x_spin, self.y_spin,
                  self.text_edit, self.size_spin, self.color_edit):
            w.setEnabled(True)
        self._title.setText(f"{elem.type_name} (page {elem.page + 1})")
        self.name_edit.setText(getattr(elem, "name", ""))
        self.x_spin.setValue(int(getattr(elem, "x", getattr(elem, "x1", 0)) or 0))
        self.y_spin.setValue(int(getattr(elem, "y", getattr(elem, "y1", 0)) or 0))
        self.text_edit.setText(str(getattr(elem, "text", "")))
        self.size_spin.setValue(int(getattr(elem, "size", 12)))
        self.color_edit.setText(getattr(elem, "color", "#000000"))

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self.color_edit.text() or "#000000"),
                                      self, "Element color")
        if color.isValid():
            self.color_edit.setText(color.name())

    def _apply(self):
        elem = self.controller.selected_element()
        if elem is None:
            return
        if hasattr(elem, "name"):
            elem.name = self.name_edit.text()
        if hasattr(elem, "x"):
            elem.x = self.x_spin.value()
        if hasattr(elem, "y"):
            elem.y = self.y_spin.value()
        if hasattr(elem, "text"):
            elem.text = self.text_edit.text()
        if hasattr(elem, "size"):
            elem.size = self.size_spin.value()
        if hasattr(elem, "color"):
            elem.color = self.color_edit.text()
        self.element_edited.emit()
