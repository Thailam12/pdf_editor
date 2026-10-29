# -*- coding: utf-8 -*-
"""PyQt6 main window for the PDFMind editor."""
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QLabel, QDockWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QInputDialog,
    QApplication, QMenu, QSlider, QToolButton,
)

from win32.pyqt6_app.document_controller import DocumentController
from win32.pyqt6_app.pdf_canvas import PdfCanvas
from win32.pyqt6_app.panels import PageList, LayersPanel, PropertiesPanel
from win32.pyqt6_app.editor_facade import EditorFacade
from win32.pyqt6_app.features import build_menus
from win32.pyqt6_app import tk_bridge
from win32.pyqt6_app.qat import QuickAccessToolbar, QatRunner
from win32.pyqt6_app.ribbon import Ribbon
from win32.models.elements import TextElement, ImageElement


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDFMind AI — Ultimate PDF Editor (PyQt6)")
        self.resize(1400, 900)
        self.controller = DocumentController(self)
        self.canvas = PdfCanvas(self.controller, self)
        self._build_actions()
        self._build_menus()
        self.menuBar().setVisible(False)  # Word uses a ribbon, not a menu bar
        self._build_docks()
        self._build_status_bar()
        self._connect()
        # Facade exposes the legacy ``editor`` contract to the reused services,
        # and the tk->Qt bridge keeps their messagebox/filedialog calls native.
        self.facade = EditorFacade(self.controller, self)
        tk_bridge.install(lambda: self)
        build_menus(self)
        # Quick-Access Toolbar (reuses the same command ids as the legacy QAT).
        self.qat = QatRunner(self)
        self.qat_toolbar = QuickAccessToolbar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.qat_toolbar)
        if self.qat_toolbar.position == "below":
            self.apply_qat_position("below")
        self._add_qat_view_toggle()
        # Word-style ribbon sits directly above the canvas.
        self.ribbon = Ribbon(self)
        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self.ribbon)
        cl.addWidget(self.canvas, 1)
        self.setCentralWidget(central)
        self._update_actions()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    def _act(self, text, slot, shortcut=None, icon=None):
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        if icon:
            action.setIcon(QIcon(icon))
        action.triggered.connect(slot)
        return action

    def _build_actions(self):
        c = self.controller
        self.a_new = self._act("&New", self.new_document, "Ctrl+N")
        self.a_open = self._act("&Open…", self.on_open, "Ctrl+O")
        self.a_save = self._act("&Save", self.on_save, "Ctrl+S")
        self.a_save_as = self._act("Save &As…", self.on_save_as, "Ctrl+Shift+S")
        self.a_exit = self._act("E&xit", self.close, "Ctrl+Q")
        self.a_undo = self._act("&Undo", c.undo, "Ctrl+Z")
        self.a_redo = self._act("&Redo", c.redo, "Ctrl+Y")
        self.a_delete = self._act("&Delete element", c.remove_selected, "Delete")
        self.a_text = self._act("Add &Text", self.on_add_text, "Ctrl+T")
        self.a_image = self._act("Add &Image", self.on_add_image, "Ctrl+G")
        self.a_zoom_in = self._act("Zoom &In", c.zoom_in, "Ctrl++")
        self.a_zoom_out = self._act("Zoom &Out", c.zoom_out, "Ctrl+-")
        self.a_fit = self._act("&Fit Page", self.canvas.fit_to_view, "Ctrl+0")
        self.a_rotate = self._act("&Rotate page", c.rotate_current, "Ctrl+R")
        self.a_del_page = self._act("Delete &Page", c.delete_current_page)
        self.a_prev = self._act("&Previous page", c.prev_page, "Alt+Left")
        self.a_next = self._act("&Next page", c.next_page, "Alt+Right")
        self.a_about = self._act("&About", self.on_about)

    def _build_menus(self):
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        for a in (self.a_new, None, self.a_open, self.a_save, self.a_save_as,
                  None, self.a_exit):
            m_file.addSeparator() if a is None else m_file.addAction(a)
        m_edit = mb.addMenu("&Edit")
        for a in (self.a_undo, self.a_redo, None, self.a_delete):
            m_edit.addSeparator() if a is None else m_edit.addAction(a)
        m_insert = mb.addMenu("&Insert")
        m_insert.addAction(self.a_text)
        m_insert.addAction(self.a_image)
        m_view = mb.addMenu("&View")
        for a in (self.a_zoom_in, self.a_zoom_out, self.a_fit):
            m_view.addAction(a)
        m_page = mb.addMenu("&Page")
        for a in (self.a_prev, self.a_next, self.a_rotate, self.a_del_page):
            m_page.addAction(a)
        m_help = mb.addMenu("&Help")
        m_help.addAction(self.a_about)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        for a in (self.a_new, self.a_open, self.a_save, None, self.a_undo, self.a_redo,
                  None, self.a_text, self.a_image, None,
                  self.a_zoom_out, self.a_zoom_in, self.a_fit, None,
                  self.a_prev, self.a_next, self.a_rotate):
            tb.addSeparator() if a is None else tb.addAction(a)

    def _build_docks(self):
        self.page_list = PageList(self.controller, self)
        left = QDockWidget("Pages", self)
        left.setWidget(self.page_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, left)

        right_container = QWidget()
        rl = QVBoxLayout(right_container)
        self.layers = LayersPanel(self.controller, right_container)
        self.props = PropertiesPanel(self.controller, right_container)
        rl.addWidget(QLabel("Layers"))
        rl.addWidget(self.layers, 2)
        rl.addWidget(QLabel("Properties"))
        rl.addWidget(self.props, 2)
        right = QDockWidget("Inspector", self)
        right.setWidget(right_container)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, right)

    def _build_status_bar(self):
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.setStatusBar(sb)
        self._page_label = QLabel("No document")
        self._elem_label = QLabel("")
        self._status_label = QLabel("Ready")
        sb.addWidget(self._page_label)
        sb.addWidget(self._elem_label)
        sb.addWidget(self._status_label, 1)

        # Right side: view-mode buttons + zoom control (Word-style).
        for text, tip, slot in (("\U0001f4d6", "Read / Fit Page", self.canvas.fit_to_view),
                                ("\u2194", "Fit Width", lambda: self.qat.run("zoom_width")),
                                ("100%", "Actual Size", lambda: self.controller.set_zoom(100))):
            btn = QToolButton()
            btn.setText(text)
            btn.setToolTip(tip)
            btn.setAutoRaise(True)
            btn.clicked.connect(slot)
            sb.addPermanentWidget(btn)

        sb.addPermanentWidget(QLabel("  \u2212"))
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 400)
        self._zoom_slider.setSingleStep(10)
        self._zoom_slider.setFixedWidth(130)
        self._zoom_slider.setValue(self.controller.zoom)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider)
        sb.addPermanentWidget(self._zoom_slider)
        sb.addPermanentWidget(QLabel("+"))
        self._zoom_label = QLabel("100% ")
        sb.addPermanentWidget(self._zoom_label)

    def _on_zoom_slider(self, value):
        self.controller.set_zoom(value)

    def search_from_box(self, text):
        """Run a real full-text search from the ribbon's Search box."""
        if not self.controller.has_document:
            self._require_document()
            return
        try:
            results = self.facade.search_service.search_text(text)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "Search failed", str(e))
            return
        if not results:
            QMessageBox.information(self, "Find", f"No matches for {text!r}.")
            return
        self.controller.set_current_page(results[0]["page"])
        self._set_status(f"{len(results)} match(es) for {text!r}")

    def _connect(self):
        c = self.controller
        c.document_loaded.connect(self._on_document_loaded)
        c.page_changed.connect(self._on_page_changed)
        c.elements_changed.connect(self._refresh_elements)
        c.selection_changed.connect(self._on_selection)
        c.undo_state_changed.connect(lambda *_: self._update_actions())
        c.modified_changed.connect(self._on_modified)
        self.canvas.selection_requested.connect(c.select)
        self.canvas.delete_requested.connect(c.remove_selected)
        self.canvas.move_requested.connect(c.move_selected)
        self.canvas.zoom_requested.connect(c.set_zoom)
        self.page_list.page_selected.connect(c.set_current_page)
        self.layers.layer_selected.connect(c.select)
        self.props.element_edited.connect(self._refresh_elements)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def new_document(self):
        """Create a blank one-page PDF and open it as a temporary document."""
        import tempfile
        if self.controller._modified:
            r = QMessageBox.question(
                self, "Unsaved changes",
                "Save changes to the current document first?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel)
            if r == QMessageBox.StandardButton.Cancel:
                return
            if r == QMessageBox.StandardButton.Save:
                self.on_save()
                if self.controller._modified:
                    return  # save was cancelled
        fd, path = tempfile.mkstemp(suffix=".pdf", prefix="pdfmind_new_")
        os.close(fd)
        try:
            from win32.new_file_template import create_blank_pdf
            create_blank_pdf(path)
            self.controller.open(path)
            self.facade.is_temp_document = True
            self._set_status("New blank document created")
        except Exception as e:
            try:
                os.remove(path)
            except OSError:
                pass
            QMessageBox.critical(self, "New failed", str(e))

    def on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "",
                                              "PDF Files (*.pdf)")
        if path:
            try:
                self.controller.open(path)
                self._set_status(f"Opened {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Open failed", str(e))

    def on_save(self):
        if not self.controller.path:
            return self.on_save_as()
        try:
            self.controller.save()
            self._set_status(f"Saved {os.path.basename(self.controller.path)}")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def on_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF As", "",
                                              "PDF Files (*.pdf)")
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            try:
                self.controller.save(path)
                self._set_status(f"Saved {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Save failed", str(e))

    def on_add_text(self):
        if not self.controller.has_document:
            self._require_document()
            return
        text, ok = QInputDialog.getText(self, "Add Text", "Text:")
        if ok and text:
            self.controller.add_element(
                TextElement(text=text, x=72, y=72, size=16,
                            page=self.controller.current_page))
            self._set_status("Added text element")

    def on_add_image(self):
        if not self.controller.has_document:
            self._require_document()
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Insert Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path:
            self.controller.add_element(
                ImageElement(path=path, x=72, y=72, w=200, h=150,
                             page=self.controller.current_page))
            self._set_status("Added image element")

    def on_about(self):
        QMessageBox.about(
            self, "About PDFMind",
            "PDFMind AI — Ultimate PDF Editor\n\n"
            "PyQt6 desktop build.\nLocal-only processing.")

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _on_document_loaded(self):
        self.page_list.reload_pages()
        self.canvas.refresh()
        self._refresh_elements()
        self._update_actions()

    def _on_page_changed(self, index):
        self.canvas.refresh()
        self.page_list.set_current(index)
        self._refresh_elements()
        self._page_label.setText(
            f"Page {index + 1} of {self.controller.total_pages}")
        self._sync_zoom()

    def _refresh_elements(self):
        self.canvas.refresh()
        self.layers.reload()
        self.props.show_element(self.controller.selected_index)
        n = len(self.controller.elements)
        self._elem_label.setText(f"{n} element(s)" if self.controller.has_document else "")

    def _on_selection(self, index):
        self.canvas.refresh()
        self.layers.select_element(index if index >= 0 else None)
        self.props.show_element(index if index >= 0 else None)

    def _on_modified(self, modified):
        self.setWindowModified(modified)
        base = os.path.basename(self.controller.path) if self.controller.path \
            else "PDFMind AI"
        self.setWindowTitle(f"{'*' if modified else ''}{base} — PDFMind (PyQt6)")

    def _update_actions(self):
        c = self.controller
        has = c.has_document
        self.a_save.setEnabled(has)
        self.a_save_as.setEnabled(has)
        self.a_delete.setEnabled(c.selected_index is not None)
        self.a_rotate.setEnabled(has)
        self.a_del_page.setEnabled(has and c.total_pages > 1)
        self.a_prev.setEnabled(has and c.current_page > 0)
        self.a_next.setEnabled(has and c.current_page < c.total_pages - 1)
        self.a_zoom_in.setEnabled(has)
        self.a_zoom_out.setEnabled(has)
        self.a_fit.setEnabled(has)
        self._zoom_label.setText(f"{c.zoom}% ")
        if hasattr(self, "_zoom_slider"):
            self._zoom_slider.blockSignals(True)
            self._zoom_slider.setValue(c.zoom)
            self._zoom_slider.blockSignals(False)

    def _sync_zoom(self):
        z = self.controller.zoom
        self._zoom_label.setText(f"{z}% ")
        if hasattr(self, "_zoom_slider"):
            self._zoom_slider.blockSignals(True)
            self._zoom_slider.setValue(z)
            self._zoom_slider.blockSignals(False)

    def _require_document(self):
        QMessageBox.information(self, "No document", "Open a PDF document first.")

    def apply_qat_position(self, position):
        """Move the Quick-Access Toolbar above or below the ribbon/menus."""
        area = (Qt.ToolBarArea.BottomToolBarArea if position == "below"
                else Qt.ToolBarArea.TopToolBarArea)
        self.removeToolBar(self.qat_toolbar)
        self.addToolBar(area, self.qat_toolbar)
        self.qat_toolbar.setVisible(True)

    def _add_qat_view_toggle(self):
        m_view = next((m for m in self.menuBar().findChildren(QMenu)
                       if m.title() == "&View"), None)
        if m_view:
            act = QAction("Show Quick Access Toolbar", self)
            act.setCheckable(True)
            act.setChecked(True)
            act.toggled.connect(self.qat_toolbar.setVisible)
            m_view.addAction(act)

    def _set_status(self, text):
        self._status_label.setText(text)


def run(argv_file=None):
    app = QApplication.instance() or QApplication([])
    win = MainWindow()
    win.show()
    if argv_file and os.path.exists(argv_file):
        win.controller.open(os.path.abspath(argv_file))
    return app.exec()
