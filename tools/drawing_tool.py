# -*- coding: utf-8 -*-
class DrawingTool:
    def __init__(self, editor):
        self.editor = editor
        self.start_x = self.start_y = 0
        self.temp_item = None
        self.shape_type = None
        self.canvas = None

    def start_drawing(self, canvas, shape_type):
        self.shape_type = shape_type
        self.canvas = canvas
        self.start_x = self.start_y = 0
        # Temporarily disable regular canvas click handlers while drawing
        canvas.unbind("<Button-1>")
        canvas.unbind("<Motion>")
        canvas.bind("<ButtonPress-1>", self.on_press)
        canvas.bind("<B1-Motion>", self.on_drag)
        canvas.bind("<ButtonRelease-1>", self.on_release)
        canvas.configure(cursor="tcross")
        self.editor.status.configure(text=f"Đang vẽ {shape_type}... Nhấn và kéo chuột")

    def on_press(self, event):
        scale = self.editor.zoom_level / 100
        self.start_x = event.x / scale
        self.start_y = event.y / scale

    def on_drag(self, event):
        if self.temp_item:
            self.editor.canvas_preview.delete(self.temp_item)

        scale = self.editor.zoom_level / 100
        x1 = self.start_x * scale
        y1 = self.start_y * scale
        x2 = event.x
        y2 = event.y

        if self.shape_type == "line":
            self.temp_item = self.editor.canvas_preview.create_line(
                x1, y1, x2, y2, width=2, fill="red")
        elif self.shape_type == "rect":
            self.temp_item = self.editor.canvas_preview.create_rectangle(
                x1, y1, x2, y2, outline="red", width=2)
        elif self.shape_type == "ellipse":
            self.temp_item = self.editor.canvas_preview.create_oval(
                x1, y1, x2, y2, outline="red", width=2)
        elif self.shape_type == "triangle":
            self.temp_item = self.editor.canvas_preview.create_polygon(
                x1 + (x2 - x1) / 2, y1,
                x1, y2,
                x2, y2,
                outline="red", fill='', width=2)

    def on_release(self, event):
        scale = self.editor.zoom_level / 100
        end_x = event.x / scale
        end_y = event.y / scale

        if self.temp_item:
            self.editor.canvas_preview.delete(self.temp_item)
            self.temp_item = None

        if abs(end_x - self.start_x) < 5 and abs(end_y - self.start_y) < 5:
            self.editor.status.configure(text="Vẽ bị hủy: Kích thước quá nhỏ")
        else:
            from models import LineElement, ShapeElement
            self.editor.undo_manager.save_state(self.editor.elements)
            if self.shape_type == "line":
                self.editor.elements.append(LineElement(
                    x1=self.start_x, y1=self.start_y,
                    x2=end_x, y2=end_y,
                    color="red", width=2,
                    page=self.editor.current_page
                ))
            elif self.shape_type == "rect":
                self.editor.elements.append(ShapeElement(
                    shape_type="rect",
                    x=self.start_x, y=self.start_y,
                    w=end_x - self.start_x, h=end_y - self.start_y,
                    color="red",
                    page=self.editor.current_page
                ))
            elif self.shape_type == "ellipse":
                self.editor.elements.append(ShapeElement(
                    shape_type="ellipse",
                    x=self.start_x, y=self.start_y,
                    w=end_x - self.start_x, h=end_y - self.start_y,
                    color="red",
                    page=self.editor.current_page
                ))
            elif self.shape_type == "triangle":
                self.editor.elements.append(ShapeElement(
                    shape_type="triangle",
                    x=self.start_x, y=self.start_y,
                    w=end_x - self.start_x, h=end_y - self.start_y,
                    color="red",
                    page=self.editor.current_page
                ))
            self.editor.canvas_manager.update_preview()
            self.editor.update_info_panel()
            self.editor.status.configure(text=f"Đã vẽ {self.shape_type}")

        self.editor.canvas_preview.unbind("<ButtonPress-1>")
        self.editor.canvas_preview.unbind("<B1-Motion>")
        self.editor.canvas_preview.unbind("<ButtonRelease-1>")
        self.editor.canvas_preview.bind("<Button-1>", self.editor.on_canvas_click)
        self.editor.canvas_preview.bind("<B1-Motion>", self.editor.on_canvas_drag)
        self.editor.canvas_preview.bind("<ButtonRelease-1>", self.editor.on_canvas_release)
        self.editor.canvas_preview.bind("<Motion>", self.editor.on_canvas_motion)
        self.editor.canvas_preview.configure(cursor="cross")
        self.shape_type = None
