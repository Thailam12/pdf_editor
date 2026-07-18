import math
from models.elements import LineElement


class MeasurementService:
    def __init__(self, editor):
        self.editor = editor
        self._pixels_per_unit = 96.0
        self._unit = "mm"
        self._conversion_factors = {
            "mm": 25.4,
            "cm": 2.54,
            "m": 0.0254,
            "in": 1.0,
            "ft": 1.0 / 12.0,
        }
        self._measurements = []

    def measure_distance(self, x1, y1, x2, y2, scale=None):
        """Measure distance between two points and return value in current unit."""
        try:
            pixels = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            px_per = scale or self._pixels_per_unit
            inches = pixels / px_per
            factor = self._conversion_factors.get(self._unit, 25.4)
            return round(inches * factor, 2)
        except Exception as e:
            raise RuntimeError(f"Distance measurement failed: {e}")

    def measure_perimeter(self, points, scale=None):
        """Measure the total perimeter of a polygon defined by points."""
        try:
            if not points or len(points) < 2:
                return 0.0
            px_per = scale or self._pixels_per_unit
            total = 0.0
            for i in range(len(points)):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % len(points)]
                total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            inches = total / px_per
            factor = self._conversion_factors.get(self._unit, 25.4)
            return round(inches * factor, 2)
        except Exception as e:
            raise RuntimeError(f"Perimeter measurement failed: {e}")

    def measure_area(self, points, scale=None):
        """Measure the area of a polygon using the shoelace formula."""
        try:
            if not points or len(points) < 3:
                return 0.0
            px_per = scale or self._pixels_per_unit
            n = len(points)
            area_px = 0.0
            for i in range(n):
                j = (i + 1) % n
                area_px += points[i][0] * points[j][1]
                area_px -= points[j][0] * points[i][1]
            area_px = abs(area_px) / 2.0
            factor = self._conversion_factors.get(self._unit, 25.4)
            return round(area_px / (px_per ** 2) * (factor ** 2), 2)
        except Exception as e:
            raise RuntimeError(f"Area measurement failed: {e}")

    def add_measurement_element(self, measurement_type, points, scale=None, unit=None):
        """Add a measurement element to the editor. Returns a LineElement."""
        try:
            self.editor.undo_manager.save_state(self.editor.elements)
            if unit:
                old_unit = self._unit
                self._unit = unit
            if measurement_type == "distance" and len(points) >= 2:
                x1, y1 = points[0]
                x2, y2 = points[1]
                value = self.measure_distance(x1, y1, x2, y2, scale)
                elem = LineElement(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    color="#FF0000", width=2,
                    page=self.editor.current_page
                )
                elem.name = f"{value} {unit or self._unit}"
                self.editor.elements.append(elem)
                self._measurements.append({
                    "type": "distance", "value": value,
                    "unit": unit or self._unit, "points": points
                })
            elif measurement_type == "perimeter" and len(points) >= 2:
                value = self.measure_perimeter(points, scale)
                for i in range(len(points)):
                    x1, y1 = points[i]
                    x2, y2 = points[(i + 1) % len(points)]
                    elem = LineElement(
                        x1=x1, y1=y1, x2=x2, y2=y2,
                        color="#0000FF", width=1,
                        page=self.editor.current_page
                    )
                    self.editor.elements.append(elem)
                self._measurements.append({
                    "type": "perimeter", "value": value,
                    "unit": unit or self._unit, "points": points
                })
            elif measurement_type == "area" and len(points) >= 3:
                value = self.measure_area(points, scale)
                for i in range(len(points)):
                    x1, y1 = points[i]
                    x2, y2 = points[(i + 1) % len(points)]
                    elem = LineElement(
                        x1=x1, y1=y1, x2=x2, y2=y2,
                        color="#00AA00", width=1,
                        page=self.editor.current_page
                    )
                    self.editor.elements.append(elem)
                self._measurements.append({
                    "type": "area", "value": value,
                    "unit": unit or self._unit, "points": points
                })
            if unit:
                self._unit = old_unit
            self.editor.canvas_manager.update_preview()
            return elem
        except Exception as e:
            raise RuntimeError(f"Cannot add measurement: {e}")

    def set_scale(self, pixels_per_unit):
        """Set the scale factor (pixels per unit)."""
        self._pixels_per_unit = max(1.0, float(pixels_per_unit))

    def set_unit(self, unit_name):
        """Set the measurement unit. Supported: mm, cm, m, in, ft."""
        if unit_name in self._conversion_factors:
            self._unit = unit_name
        else:
            raise ValueError(f"Unsupported unit: {unit_name}. Use mm, cm, m, in, ft.")
