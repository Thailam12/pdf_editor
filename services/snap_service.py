import math


class SnapService:
    def __init__(self, editor):
        self.editor = editor
        self._snap_enabled = True
        self._grid_visible = False
        self._grid_size = 20.0
        self._guides = {}
        self._next_guide_id = 1

    def toggle_grid(self, show):
        """Show or hide the grid overlay."""
        self._grid_visible = show
        try:
            self.editor.canvas_manager.update_preview()
        except Exception:
            pass

    def set_grid_size(self, spacing):
        """Set the grid spacing in pixels."""
        self._grid_size = max(5.0, float(spacing))

    def snap_to_grid(self, x, y):
        """Snap coordinates to the nearest grid point. Returns (snapped_x, snapped_y)."""
        if not self._snap_enabled:
            return (x, y)
        sx = round(x / self._grid_size) * self._grid_size
        sy = round(y / self._grid_size) * self._grid_size
        return (sx, sy)

    def add_guide(self, orientation, position):
        """Add a guide line. orientation: 'horizontal' or 'vertical'."""
        try:
            guide_id = self._next_guide_id
            self._next_guide_id += 1
            self._guides[guide_id] = {
                "id": guide_id,
                "orientation": orientation,
                "position": float(position)
            }
            try:
                self.editor.canvas_manager.update_preview()
            except Exception:
                pass
            return guide_id
        except Exception as e:
            raise RuntimeError(f"Cannot add guide: {e}")

    def remove_guide(self, guide_id):
        """Remove a guide by its ID."""
        try:
            if guide_id in self._guides:
                del self._guides[guide_id]
                try:
                    self.editor.canvas_manager.update_preview()
                except Exception:
                    pass
        except Exception as e:
            raise RuntimeError(f"Cannot remove guide: {e}")

    def snap_to_guides(self, x, y, tolerance=10):
        """Snap coordinates to the nearest guide if within tolerance. Returns (snapped_x, snapped_y)."""
        if not self._snap_enabled:
            return (x, y)
        snapped_x = x
        snapped_y = y
        for guide in self._guides.values():
            if guide["orientation"] == "vertical":
                dist = abs(x - guide["position"])
                if dist <= tolerance:
                    snapped_x = guide["position"]
            elif guide["orientation"] == "horizontal":
                dist = abs(y - guide["position"])
                if dist <= tolerance:
                    snapped_y = guide["position"]
        return (snapped_x, snapped_y)

    def get_guides(self):
        """Return list of all guides."""
        return list(self._guides.values())

    def clear_guides(self):
        """Remove all guides."""
        self._guides.clear()
        try:
            self.editor.canvas_manager.update_preview()
        except Exception:
            pass

    def toggle_snap(self, enabled):
        """Enable or disable snap behavior globally."""
        self._snap_enabled = enabled
