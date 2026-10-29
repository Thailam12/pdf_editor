# -*- coding: utf-8 -*-
"""PyQt6 PDF page canvas: renders the current page and overlays elements."""
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QImage, QCursor,
)
from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsItem,
    QMenu, QGraphicsSimpleTextItem,
)

from win32.pyqt6_app.render import render_page


def _qcolor(value, default="#000000"):
    return QColor(value or default)


class ElementItem(QGraphicsItem):
    """A single editable overlay element drawn in device (zoomed) pixels."""

    def __init__(self, element, scale, index, scene):
        super().__init__()
        self.element = element
        self.scale = scale
        self.index = index
        self._scene = scene
        self.selected = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self._bounds = self._compute_bounds()

    def _compute_bounds(self):
        s = self.scale
        e = self.element
        if hasattr(e, "get_bounds"):
            x, y, w, h = e.get_bounds()
            return QRectF(x * s, y * s, max(1, w * s), max(1, h * s))
        return QRectF(0, 0, 10, 10)

    def boundingRect(self):
        return self._bounds.adjusted(-4, -4, 4, 4)

    def paint(self, painter: QPainter, option, widget=None):
        e = self.element
        s = self.scale
        etype = getattr(e, "type_name", "")
        # ShapeElement stores its kind in shape_type, not type_name.
        if etype == "shape":
            etype = getattr(e, "shape_type", "rect") or "rect"
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if etype == "text":
            color = _qcolor(getattr(e, "color", "#000000"))
            font = QFont(getattr(e, "font_name", "Arial"))
            font.setPointSizeF(max(1, getattr(e, "size", 12) * s * 0.75))
            font.setBold(getattr(e, "bold", False))
            font.setItalic(getattr(e, "italic", False))
            font.setUnderline(getattr(e, "underline", False))
            painter.setFont(font)
            painter.setPen(color)
            b = self._bounds
            painter.drawText(b, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                             getattr(e, "text", ""))
        elif etype == "image":
            path = getattr(e, "path", "")
            img = QImage(path)
            if not img.isNull():
                painter.drawImage(self._bounds, img)
        elif etype == "line":
            pen = QPen(_qcolor(getattr(e, "color", "#ff0000")),
                       max(1, getattr(e, "width", 2) * s))
            painter.setPen(pen)
            painter.drawLine(e.x1 * s, e.y1 * s, e.x2 * s, e.y2 * s)
        elif etype in ("rect", "ellipse", "triangle"):
            pen = QPen(_qcolor(getattr(e, "color", "#ff0000")),
                       max(1, getattr(e, "stroke_width", 2) * s))
            painter.setPen(pen)
            if getattr(e, "filled", False):
                painter.setBrush(QBrush(_qcolor(getattr(e, "fill_color", "#ff0000"))))
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
            if etype == "rect":
                painter.drawRect(self._bounds)
            elif etype == "ellipse":
                painter.drawEllipse(self._bounds)
            else:
                from PyQt6.QtGui import QPolygonF
                poly = QPolygonF([
                    QPointF(e.x * s + e.w * s / 2, e.y * s),
                    QPointF(e.x * s, (e.y + e.h) * s),
                    QPointF((e.x + e.w) * s, (e.y + e.h) * s),
                ])
                painter.drawPolygon(poly)
        elif etype == "highlight":
            color = _qcolor(getattr(e, "color", "#FFFF00"))
            color.setAlphaF(getattr(e, "opacity", 0.4))
            painter.fillRect(self._bounds, color)
        elif etype == "redact":
            painter.fillRect(self._bounds, _qcolor(getattr(e, "color", "#000000")))
        elif etype == "note":
            painter.setBrush(QBrush(_qcolor(getattr(e, "color", "#FFA500"))))
            painter.setPen(QPen(QColor("#000000")))
            painter.drawRect(self._bounds)
        elif etype in ("annotation", "link", "form_field", "watermark", "bates", "shape"):
            # Generic outlined box for annotation-like overlays (underline/link/etc.).
            painter.setPen(QPen(_qcolor(getattr(e, "color", "#89b4fa")),
                                max(1, getattr(e, "stroke_width", 2) * s)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            b = self._bounds
            style = getattr(e, "style", "")
            if style in ("underline", "strikethrough", "squiggly"):
                y = b.bottom() - b.height() / 2 if style == "strikethrough" else b.bottom() - 1
                painter.drawLine(QPointF(b.left(), y), QPointF(b.right(), y))
            else:
                painter.drawRect(b)
        else:
            painter.setPen(QPen(QColor("#89b4fa")))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._bounds)

        if self.selected:
            pen = QPen(QColor("#89b4fa"), 1.5, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(self._bounds)


class PdfCanvas(QGraphicsView):
    selection_requested = pyqtSignal(int)
    delete_requested = pyqtSignal()
    move_requested = pyqtSignal(float, float)
    zoom_requested = pyqtSignal(int)

    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor("#181825"))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def refresh(self):
        self._scene.clear()
        page = self.controller.page()
        if page is None:
            return
        scale = self.controller.zoom / 100.0
        pixmap = render_page(page, scale)
        pix_item = QGraphicsPixmapItem(pixmap)
        self._scene.addItem(pix_item)
        for idx, elem in self.controller.elements_on_current_page():
            item = ElementItem(elem, scale, idx, self._scene)
            item.selected = (idx == self.controller.selected_index)
            item.setZValue(10)
            self._scene.addItem(item)
        self._scene.setSceneRect(0, 0, pixmap.width(), pixmap.height())

    def fit_to_view(self):
        page = self.controller.page()
        if page is None:
            return
        vp = self.viewport().size()
        self.controller.zoom_fit(vp.width() - 20, vp.height() - 20)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.controller.zoom_in()
            elif delta < 0:
                self.controller.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            hit = self._item_at(scene_pos)
            if hit is not None:
                self.selection_requested.emit(hit.index)
                self._drag_start = scene_pos
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                super().mousePressEvent(event)
                return
        self._drag_start = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, "_drag_start", None) is not None and \
                event.buttons() & Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            dx = scene_pos.x() - self._drag_start.x()
            dy = scene_pos.y() - self._drag_start.y()
            if abs(dx) >= 2 or abs(dy) >= 2:
                scale = max(0.01, self.controller.zoom / 100.0)
                self.move_requested.emit(dx / scale, dy / scale)
                self._drag_start = scene_pos
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_start = None
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        super().mouseReleaseEvent(event)

    def _item_at(self, scene_pos):
        for item in self._scene.items(scene_pos):
            if isinstance(item, ElementItem):
                return item
        return None

    def contextMenuEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        hit = self._item_at(scene_pos)
        if hit is not None:
            self.selection_requested.emit(hit.index)
        menu = QMenu(self)
        act_del = menu.addAction("Delete element")
        act_del.triggered.connect(self.delete_requested.emit)
        menu.exec(event.globalPos())
