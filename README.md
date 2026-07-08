 # Word-like Super PDF Editor v2.0

A powerful Python-based PDF editor with a Word-like interface, featuring rich text formatting, drawing tools, and advanced editing capabilities.

## Features

### 📝 Text Editing
- **Insert text** with full formatting control
- **Font selection**: Arial, Times New Roman, Courier, Calibri
- **Font sizes**: 8pt to 72pt
- **Text styling**: Bold, Italic, Underline
- **Text alignment**: Left, Center, Right
- **Text color**: Full color palette with color picker
- **Position control**: Precise X, Y positioning in inches

### 🖼️ Image Handling
- **Insert images** (PNG, JPG, JPEG, GIF, BMP)
- **Resize images** with width and height control
- **Position images** anywhere on the page
- **Visual preview** of image placement

### 🎨 Drawing Tools
- **Lines**: Draw straight lines with customizable colors
- **Rectangles**: Create rectangular shapes
- **Ellipses**: Draw oval/circular shapes
- **Real-time preview** of shapes while drawing
- **Multiple colors**: Red, blue, and custom colors

### ↩️ Undo/Redo
- **Full undo/redo stack** (up to 50 actions)
- **Keyboard shortcuts**: Ctrl+Z (Undo), Ctrl+Y (Redo)
- **Visual status** showing undo/redo availability

### 🔧 Element Management
- **Select elements** by clicking on them
- **Edit selected elements** (especially text)
- **Delete elements** with Delete key or context menu
- **View element properties** in the right panel
- **Statistics panel** showing element counts

### 🔍 View Controls
- **Zoom levels**: 50% to 200%
- **Zoom shortcuts**: Phóng to, Thu nhỏ, Phù hợp trang
- **Real-time zoom**: Instant preview updates

### 💾 File Management
- **Open PDF files** with full document support
- **Save edited PDFs** with all modifications
- **Export as PDF** with new formatting
- **Print PDFs** directly to default printer

### 📊 Document Information
- **Page counter**: Shows current page and total pages
- **Element counter**: Displays total elements
- **Statistics**: Counts text, images, and shapes
- **Status bar**: Real-time operation feedback

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open PDF |
| Ctrl+S | Save PDF |
| Ctrl+P | Print PDF |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+B | Bold |
| Ctrl+I | Italic |
| Ctrl+U | Underline |
| Delete | Delete selected element |

## User Interface

### Main Toolbar
- **File operations**: Open, Save, Print
- **Edit operations**: Undo, Redo
- **Insert operations**: Text, Image
- **Drawing tools**: Line, Rectangle, Ellipse
- **Utilities**: Clear all, Color picker

### Formatting Toolbar
- **Font selection** dropdown
- **Font size** selector
- **Text style buttons**: Bold, Italic, Underline
- **Alignment buttons**: Left, Center, Right
- **Color picker** for text color

### Property Panel (Right Sidebar)
- **Zoom slider**: Adjust view scale
- **Page information**: Current page and total pages
- **Element counter**: Number of elements on page
- **Statistics**: Breakdown of element types

## How to Use

### Basic Workflow
1. **Open a PDF**: Click "Mở PDF" or press Ctrl+O
2. **Add elements**: Use toolbar buttons or menus
3. **Format text**: Select font, size, style, and color
4. **Add drawings**: Use drawing tools
5. **Save**: Click "Lưu PDF" or press Ctrl+S

### Adding Text
1. Click "🔠 Chèn Chữ" button
2. Enter text content
3. Set position (X, Y in inches)
4. Choose font and size
5. Select text color
6. Click "Áp dụng"

### Adding Images
1. Click "🖼️ Chèn Ảnh" button
2. Select image file
3. Set position and dimensions
4. Click "Áp dụng"

### Drawing Shapes
1. Click the shape button (─, □, or ○)
2. Click and drag on canvas
3. Release to finish drawing

### Selecting and Editing
1. Click on an element to select it (blue highlight)
2. Right-click for context menu
3. Press Delete to remove
4. Press Ctrl+Z to undo

## Installation

### Requirements
- Python 3.8 or higher
- pip package manager

### Setup
```bash
cd d:\pdf_editor
pip install -r requirements.txt
python main.py
```

### Dependencies
- **PyMuPDF**: PDF manipulation
- **reportlab**: PDF generation
- **Pillow**: Image processing
- **python-docx**: Document handling (optional)

## Project Structure

```
pdf_editor/
├── main.py                 # Application entry point
├── editor.py              # Main editor class
├── gui_components.py      # GUI creation functions
├── pdf_utils.py           # PDF utilities
├── text_formatting.py     # Text formatting manager
├── undo_redo.py           # Undo/redo functionality
├── requirements.txt       # Python dependencies
├── static/                # Static assets
└── tools/
    ├── __init__.py
    ├── text_tool.py       # Text insertion dialog
    ├── image_tool.py      # Image insertion dialog
    └── drawing_tool.py    # Drawing utilities
```

## Architecture

### Core Components

**editor.py**: Main application class
- GUI creation and management
- Event handling
- Element management
- File operations

**text_formatting.py**: Text and paragraph styling
- TextStyle class
- ParagraphStyle class
- FormattingManager class

**undo_redo.py**: Undo/redo history management
- UndoRedoManager class
- State management

**pdf_utils.py**: PDF operations
- Load and display PDFs
- Save edited PDFs
- Element rendering

**gui_components.py**: UI creation
- Main toolbar creation
- Formatting toolbar creation
- Property panel creation

## Tips and Tricks

1. **Precision positioning**: Use Tab to move between coordinate fields
2. **Quick formatting**: Use keyboard shortcuts for faster editing
3. **Zoom efficiency**: Use the zoom slider for quick adjustments
4. **Batch operations**: Use Ctrl+Z to undo multiple actions at once
5. **Color consistency**: Use the color picker to maintain design consistency

## Limitations

- Single page editing (multi-page support in development)
- Limited PDF form support
- No OCR capabilities
- No annotation tools

## Future Enhancements

- [ ] Multi-page editing
- [ ] Find and Replace functionality
- [ ] Text search
- [ ] Advanced shape tools
- [ ] Layer management
- [ ] PDF form support
- [ ] Handwriting/annotation tools
- [ ] Template library

## Troubleshooting

### Application won't start
- Ensure Python 3.8+ is installed
- Run `pip install -r requirements.txt`
- Check for missing dependencies

### PDF won't open
- Verify the file is a valid PDF
- Check file permissions
- Ensure file is not corrupted

### Formatting not saved
- Always click "Áp dụng" before saving
- Use Ctrl+S or File > Lưu PDF
- Verify output location has write permissions

## Support

For issues or feature requests, please check:
1. Application logs
2. Python error messages
3. File permissions
4. Disk space availability

## Version History

### v2.0 (Current)
- Complete rewrite with Word-like interface
- Added text formatting options
- Implemented undo/redo system
- Added element selection and editing
- Enhanced UI with property panel
- Full keyboard shortcut support

### v1.0 (Original)
- Basic PDF editing
- Simple drawing tools
- Basic text insertion

## License

This project is provided as-is for educational purposes.

## Author

Created as a Python PDF editing solution with advanced formatting capabilities.
