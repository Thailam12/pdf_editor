"""tkinter → PyQt6 dialog bridge.

Most reusable logic services call ``tkinter.messagebox`` / ``filedialog`` /
``simpledialog`` / ``colorchooser`` for user feedback and input. Instead of
rewriting every service, this module monkey-patches those functions to show
native PyQt6 dialogs, so the services integrate cleanly into the Qt app while
keeping their real logic intact.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

# Sentinel parent provider; replaced by install() with the live main window.
_parent_provider = lambda: None  # noqa: E731


def _parent():
    return _parent_provider()


def _convert_filetypes(filetypes):
    """tkinter ``[(desc, glob), ...]`` → Qt ``"Desc (*.glob);;..."`` filter."""
    if not filetypes:
        return ""
    parts = []
    for item in filetypes:
        try:
            desc, patterns = item[0], item[1]
        except (TypeError, IndexError):
            continue
        if isinstance(patterns, (list, tuple)):
            patterns = " ".join(patterns)
        parts.append(f"{desc} ({patterns})")
    return ";;".join(parts)


def _msgbox(kind, title, message, buttons=QMessageBox.StandardButton.Ok):
    box = QMessageBox(_parent())
    box.setWindowTitle(title or "")
    box.setText(str(message))
    box.setIcon(kind)
    box.setStandardButtons(buttons)
    box.setDefaultButton(QMessageBox.StandardButton.Ok)
    return box.exec()


# --- messagebox -------------------------------------------------------------
def _showinfo(title, message, *_, **__):
    _msgbox(QMessageBox.Icon.Information, title, message)
    return True


def _showwarning(title, message, *_, **__):
    _msgbox(QMessageBox.Icon.Warning, title, message)
    return True


def _showerror(title, message, *_, **__):
    _msgbox(QMessageBox.Icon.Critical, title, message)
    return True


def _askyesno(title, message, *_, **__):
    return _msgbox(
        QMessageBox.Icon.Question, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    ) == QMessageBox.StandardButton.Yes


def _askokcancel(title, message, *_, **__):
    return _msgbox(
        QMessageBox.Icon.Question, title, message,
        QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
    ) == QMessageBox.StandardButton.Ok


def _askyesnocancel(title, message, *_, **__):
    result = _msgbox(
        QMessageBox.Icon.Question, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        | QMessageBox.StandardButton.Cancel,
    )
    if result == QMessageBox.StandardButton.Cancel:
        return None
    return result == QMessageBox.StandardButton.Yes


def _askretrycancel(title, message, *_, **__):
    return _askokcancel(title, message)


def _askquestion(title, message, *_, **__):
    return "yes" if _askyesno(title, message) else "no"


# --- filedialog -------------------------------------------------------------
def _askopenfilename(parent=None, title="", filetypes=None, initialdir="", **__):
    path, _ = QFileDialog.getOpenFileName(
        _parent(), title or "Open", initialdir or "", _convert_filetypes(filetypes)
    )
    return path or ""


def _askopenfilenames(parent=None, title="", filetypes=None, initialdir="", **__):
    paths, _ = QFileDialog.getOpenFileNames(
        _parent(), title or "Open", initialdir or "", _convert_filetypes(filetypes)
    )
    return tuple(paths or ())


def _asksaveasfilename(parent=None, title="", filetypes=None, initialdir="",
                       defaultextension="", **__):
    path, _ = QFileDialog.getSaveFileName(
        _parent(), title or "Save", initialdir or "",
        _convert_filetypes(filetypes) + (f";;All Files (*)" if not filetypes else ""),
    )
    if path and defaultextension and not path.lower().endswith(defaultextension.lower()):
        path += defaultextension
    return path or ""


def _askdirectory(parent=None, title="", initialdir="", **__):
    return QFileDialog.getExistingDirectory(_parent(), title or "Select Folder",
                                            initialdir or "") or ""


# --- simpledialog -----------------------------------------------------------
def _askstring(title, prompt, initialvalue="", **__):
    value, ok = QInputDialog.getText(_parent(), title or "Input", prompt,
                                     text=initialvalue or "")
    return value if ok else None


def _askinteger(title, prompt, initialvalue=0, minvalue=None, maxvalue=None, **__):
    lo = minvalue if minvalue is not None else -2147483647
    hi = maxvalue if maxvalue is not None else 2147483647
    value, ok = QInputDialog.getInt(_parent(), title or "Input", prompt,
                                    initialvalue or 0, lo, hi)
    return value if ok else None


def _askfloat(title, prompt, initialvalue=0.0, minvalue=None, maxvalue=None, **__):
    lo = minvalue if minvalue is not None else -1e18
    hi = maxvalue if maxvalue is not None else 1e18
    value, ok = QInputDialog.getDouble(_parent(), title or "Input", prompt,
                                       float(initialvalue or 0.0), float(lo), float(hi), 3)
    return value if ok else None


def _ask(title, prompt, **__):
    return _askstring(title, prompt)


# --- colorchooser -----------------------------------------------------------
def _askcolor(color=None, title="", **__):
    initial = QColor(color) if color else QColor(0, 0, 0)
    chosen = QColorDialog.getColor(initial, _parent(), title or "Select Color")
    if not chosen.isValid():
        return None, None
    rgb = (chosen.red() / 255.0, chosen.green() / 255.0, chosen.blue() / 255.0)
    return chosen.name(), rgb


def install(parent_provider):
    """Redirect tkinter dialog calls to PyQt6.

    ``parent_provider`` is a zero-arg callable returning the current parent
    QWidget (the main window), so dialogs stay correctly parented.
    """
    global _parent_provider
    _parent_provider = parent_provider

    messagebox.showinfo = _showinfo
    messagebox.showwarning = _showwarning
    messagebox.showerror = _showerror
    messagebox.askyesno = _askyesno
    messagebox.askokcancel = _askokcancel
    messagebox.askyesnocancel = _askyesnocancel
    messagebox.askretrycancel = _askretrycancel
    messagebox.askquestion = _askquestion

    filedialog.askopenfilename = _askopenfilename
    filedialog.askopenfilenames = _askopenfilenames
    filedialog.askmultipleopenfilename = _askopenfilenames
    filedialog.asksaveasfilename = _asksaveasfilename
    filedialog.askdirectory = _askdirectory

    simpledialog.askstring = _askstring
    simpledialog.askinteger = _askinteger
    simpledialog.askfloat = _askfloat
    simpledialog.ask = _ask

    colorchooser.askcolor = _askcolor
