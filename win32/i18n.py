from __future__ import annotations

LANG_VI = "vi-VN"
LANG_EN = "en-US"


def get_i18n(lang: str) -> dict:
    lang = (lang or LANG_VI).lower()

    # Only UI strings are localized.
    if "en" in lang:
        return {
            "app_title": "Word-like Super PDF Editor - Python",
            "status_ready": "Ready",
            "menu_file": "File",
            "menu_edit": "Edit",
            "menu_insert": "Insert",
            "menu_format": "Format",
            "menu_view": "View",
            "menu_help": "Help",
            "file_open": "Open PDF",
            "file_save": "Save PDF",
            "file_export": "Export PDF",
            "file_print": "Print PDF",
            "file_exit": "Exit",
            "edit_undo": "Undo",
            "edit_redo": "Redo",
            "edit_clear_all": "Clear all",
            "insert_text": "Text",
            "insert_image": "Image",
            "insert_line": "Line",
            "insert_rect": "Rectangle",
            "insert_ellipse": "Ellipse",
            "insert_triangle": "Triangle",
            "format_bold": "Bold",
            "format_italic": "Italic",
            "format_underline": "Underline",
            "format_align_left": "Align left",
            "format_align_center": "Align center",
            "format_align_right": "Align right",
            "view_prev_page": "Previous page",
            "view_next_page": "Next page",
            "view_zoom_in": "Zoom in",
            "view_zoom_out": "Zoom out",
            "view_zoom_fit": "Fit to page",
            "help_about": "About",
            "dialog_open_empty": "Empty or invalid PDF file",
            "dialog_warn_no_pdf": "No PDF opened yet!",
            "dialog_warn_no_pdf_to_print": "No PDF to print!",
            "dialog_err_open": "Error opening PDF:",
            "context_delete": "Delete",
            "context_edit": "Edit",
            "context_cancel": "Cancel",
        }

    # Default: Vietnamese
    return {
        "app_title": "Word-like Super PDF Editor - Python",
        "status_ready": "Sẵn sàng",
        "menu_file": "Tệp",
        "menu_edit": "Chỉnh sửa",
        "menu_insert": "Chèn",
        "menu_format": "Định dạng",
        "menu_view": "Xem",
        "menu_help": "Trợ giúp",
        "file_open": "Mở PDF",
        "file_save": "Lưu PDF",
        "file_export": "Xuất PDF",
        "file_print": "In PDF",
        "file_exit": "Thoát",
        "edit_undo": "Hoàn tác",
        "edit_redo": "Làm lại",
        "edit_clear_all": "Xóa tất cả",
        "insert_text": "Chữ",
        "insert_image": "Ảnh",
        "insert_line": "Đường",
        "insert_rect": "Hình chữ nhật",
        "insert_ellipse": "Ellipse",
        "insert_triangle": "Tam giác",
        "format_bold": "Tô đậm",
        "format_italic": "Nghiêng",
        "format_underline": "Gạch chân",
        "format_align_left": "Căn trái",
        "format_align_center": "Căn giữa",
        "format_align_right": "Căn phải",
        "view_prev_page": "Trang trước",
        "view_next_page": "Trang sau",
        "view_zoom_in": "Phóng to",
        "view_zoom_out": "Thu nhỏ",
        "view_zoom_fit": "Phù hợp trang",
        "help_about": "Về ứng dụng",
        "dialog_open_empty": "File PDF rỗng hoặc không hợp lệ",
        "dialog_warn_no_pdf": "Chưa mở file PDF nào!",
        "dialog_warn_no_pdf_to_print": "Chưa có file PDF để in!",
        "dialog_err_open": "Lỗi khi mở PDF:",
        "context_delete": "Xóa",
        "context_edit": "Sửa",
        "context_cancel": "Hủy",
    }


def normalize_lang(lang: str) -> str:
    if not lang:
        return LANG_VI
    lang_l = lang.lower()
    if "en" in lang_l:
        return LANG_EN
    return LANG_VI

