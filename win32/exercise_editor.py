import os
import tempfile
import tkinter as tk
from PIL import Image
from unittest.mock import patch
from editor import PDFEditor


root = tk.Tk()
root.withdraw()
app = PDFEditor(root)

img_path = os.path.join(tempfile.gettempdir(), 'pdf_editor_test_image.png')
Image.new('RGB', (120, 120), color='blue').save(img_path)

for run in range(1, 4):
    app.new_temp_document()
    app.add_text_tool = None
    app.elements.append(('text', {
        'text': f'Run {run} text', 'x': 100 + run * 10, 'y': 120 + run * 10, 'size': 16 + run,
        'font_name': 'Arial', 'color': '#000000', 'bold': True if run % 2 else False,
        'italic': False, 'underline': run == 3, 'alignment': 'left', 'page': app.current_page
    }))
    app.elements.append(('rect', {'x': 80, 'y': 220 + run * 10, 'w': 120, 'h': 60, 'color': '#ff0000', 'filled': True, 'fill_color': '#f0f0f0', 'page': app.current_page}))
    app.elements.append(('ellipse', {'x': 220, 'y': 220 + run * 10, 'w': 100, 'h': 60, 'color': '#00aa00', 'filled': True, 'fill_color': '#e8ffe8', 'page': app.current_page}))
    app.elements.append(('line', {'x1': 60, 'y1': 340 + run * 10, 'x2': 260, 'y2': 380 + run * 10, 'color': '#0000ff', 'width': 2, 'page': app.current_page}))
    app.elements.append(('image', {'path': img_path, 'x': 320, 'y': 220 + run * 10, 'w': 80, 'h': 80, 'page': app.current_page}))
    app.elements.append(('triangle', {'x': 420, 'y': 220 + run * 10, 'w': 90, 'h': 70, 'color': '#990099', 'filled': True, 'fill_color': '#f5e6ff', 'page': app.current_page}))

    app.update_preview()
    app.set_zoom(100 + run * 10)
    app.toggle_bold()
    app.toggle_italic()
    app.toggle_underline()
    app.set_alignment('center')
    app.undo_redo_manager.save_state(app.elements)
    app.delete_selected_element()
    app.undo()
    app.redo()
    app.previous_page() if app.current_page > 0 else None
    app.next_page() if app.current_page < app.total_pages - 1 else None

    out_dir = os.path.join(tempfile.gettempdir(), 'pdf_editor_runs')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f'run_{run}.pdf')
    with patch('editor.filedialog.asksaveasfilename', return_value=out_path), patch('editor.messagebox.showinfo'), patch('editor.messagebox.showwarning'):
        app.save_pdf()
    app.current_pdf = out_path
    app.is_temp_document = False
    app.temp_doc_path = None
    app.current_document_dir = out_dir
    print(f'run_{run}: ok -> {out_path}')

try:
    app.export_pdf()
except Exception as exc:
    print('export_pdf error', repr(exc))

try:
    app.ocr_current_page_dialog()
except Exception as exc:
    print('ocr_current_page_dialog error', repr(exc))

root.destroy()
print('automation complete')
