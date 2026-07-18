import math
import csv
import json
import uuid
from datetime import datetime


class AdvancedMeasurementService:
    def __init__(self, editor):
        self.editor = editor
        self._unit = "mm"
        self._precision = 2
        self._scale_factor = 1.0
        self._scale_reference = None
        self._pixels_per_inch = 72.0
        self._grid_visible = False
        self._grid_size = 20
        self._snap_to_grid = False
        self._measurements = []
        self._conversion_table = {
            "mm": {"mm": 1, "cm": 0.1, "m": 0.001, "km": 0.000001, "in": 0.03937, "ft": 0.003281, "yd": 0.001094, "mi": 0.000000621371},
            "cm": {"mm": 10, "cm": 1, "m": 0.01, "km": 0.00001, "in": 0.3937, "ft": 0.03281, "yd": 0.01094, "mi": 0.00000621371},
            "m":  {"mm": 1000, "cm": 100, "m": 1, "km": 0.001, "in": 39.37, "ft": 3.281, "yd": 1.094, "mi": 0.000621371},
            "km": {"mm": 1000000, "cm": 100000, "m": 1000, "km": 1, "in": 39370, "ft": 3281, "yd": 1094, "mi": 0.621371},
            "in": {"mm": 25.4, "cm": 2.54, "m": 0.0254, "km": 0.0000254, "in": 1, "ft": 0.08333, "yd": 0.02778, "mi": 0.0000157828},
            "ft": {"mm": 304.8, "cm": 30.48, "m": 0.3048, "km": 0.0003048, "in": 12, "ft": 1, "yd": 0.3333, "mi": 0.000189394},
            "yd": {"mm": 914.4, "cm": 91.44, "m": 0.9144, "km": 0.0009144, "in": 36, "ft": 3, "yd": 1, "mi": 0.000568182},
            "mi": {"mm": 1609344, "cm": 160934, "m": 1609.34, "km": 1.60934, "in": 63360, "ft": 5280, "yd": 1760, "mi": 1},
        }

    def set_unit(self, unit):
        if unit in self._conversion_table:
            self._unit = unit
            return True
        return False

    def set_precision(self, precision):
        self._precision = max(0, min(6, precision))

    def set_scale(self, real_distance, measured_distance):
        if measured_distance > 0:
            self._scale_factor = real_distance / measured_distance
            self._scale_reference = {"real": real_distance, "measured": measured_distance}
            return True
        return False

    def measure_distance(self, x1, y1, x2, y2):
        pixels = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        inches = pixels / self._pixels_per_inch
        adjusted = inches * self._scale_factor
        converted = self._convert(adjusted, "in", self._unit)
        result = {
            "id": str(uuid.uuid4()),
            "type": "distance",
            "value": round(converted, self._precision),
            "unit": self._unit,
            "points": [(x1, y1), (x2, y2)],
            "raw_pixels": pixels,
            "timestamp": datetime.now().isoformat(),
        }
        self._measurements.append(result)
        return result

    def measure_perimeter(self, points):
        if not points or len(points) < 2:
            return {"value": 0, "unit": self._unit}
        total_pixels = 0
        segments = []
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            seg_len = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            total_pixels += seg_len
            segments.append({"from": (x1, y1), "to": (x2, y2), "length_px": seg_len})
        inches = total_pixels / self._pixels_per_inch
        converted = self._convert(inches, "in", self._unit)
        result = {
            "id": str(uuid.uuid4()),
            "type": "perimeter",
            "value": round(converted, self._precision),
            "unit": self._unit,
            "points": points,
            "segments": segments,
            "raw_pixels": total_pixels,
            "timestamp": datetime.now().isoformat(),
        }
        self._measurements.append(result)
        return result

    def measure_area(self, points):
        if not points or len(points) < 3:
            return {"value": 0, "unit": f"{self._unit}²"}
        area_sq_px = 0
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            area_sq_px += x1 * y2 - x2 * y1
        area_sq_px = abs(area_sq_px) / 2
        px_per_inch = self._pixels_per_inch * self._scale_factor
        area_sq_inches = area_sq_px / (px_per_inch ** 2)
        unit_sq = f"{self._unit}²"
        conversion = self._conversion_table.get(self._unit, {}).get("in", 1)
        area_converted = area_sq_inches * (conversion ** 2)
        result = {
            "id": str(uuid.uuid4()),
            "type": "area",
            "value": round(area_converted, self._precision),
            "unit": unit_sq,
            "points": points,
            "raw_pixels_sq": area_sq_px,
            "timestamp": datetime.now().isoformat(),
        }
        self._measurements.append(result)
        return result

    def measure_angle(self, x1, y1, vertex_x, vertex_y, x2, y2):
        v1 = (x1 - vertex_x, y1 - vertex_y)
        v2 = (x2 - vertex_x, y2 - vertex_y)
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
        mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
        if mag1 == 0 or mag2 == 0:
            angle_deg = 0
        else:
            cos_angle = max(-1, min(1, dot / (mag1 * mag2)))
            angle_deg = math.degrees(math.acos(cos_angle))
        result = {
            "id": str(uuid.uuid4()),
            "type": "angle",
            "value": round(angle_deg, self._precision),
            "unit": "degrees",
            "points": [(x1, y1), (vertex_x, vertex_y), (x2, y2)],
            "timestamp": datetime.now().isoformat(),
        }
        self._measurements.append(result)
        return result

    def measure_rectangle(self, x1, y1, x2, y2):
        w = abs(x2 - x1)
        h = abs(y2 - y1)
        width_val = self._convert(w / self._pixels_per_inch, "in", self._unit)
        height_val = self._convert(h / self._pixels_per_inch, "in", self._unit)
        perimeter = 2 * (w + h)
        area_sq_px = w * h
        px_per_inch = self._pixels_per_inch * self._scale_factor
        area_sq_inches = area_sq_px / (px_per_inch ** 2)
        conversion = self._conversion_table.get(self._unit, {}).get("in", 1)
        area_val = area_sq_inches * (conversion ** 2)
        result = {
            "id": str(uuid.uuid4()),
            "type": "rectangle",
            "width": round(width_val, self._precision),
            "height": round(height_val, self._precision),
            "area": round(area_val, self._precision),
            "perimeter": round(self._convert(perimeter / self._pixels_per_inch, "in", self._unit), self._precision),
            "unit": self._unit,
            "area_unit": f"{self._unit}²",
            "points": [(x1, y1), (x2, y1), (x2, y2), (x1, y2)],
            "timestamp": datetime.now().isoformat(),
        }
        self._measurements.append(result)
        return result

    def measure_ellipse(self, cx, cy, rx, ry):
        a = max(rx, ry)
        b = min(rx, ry)
        a_val = self._convert(a / self._pixels_per_inch, "in", self._unit)
        b_val = self._convert(b / self._pixels_per_inch, "in", self._unit)
        pi = math.pi
        approx_perimeter = pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
        area_sq_px = pi * rx * ry
        px_per_inch = self._pixels_per_inch * self._scale_factor
        area_sq_inches = area_sq_px / (px_per_inch ** 2)
        conversion = self._conversion_table.get(self._unit, {}).get("in", 1)
        area_val = area_sq_inches * (conversion ** 2)
        perimeter_val = self._convert(approx_perimeter / self._pixels_per_inch, "in", self._unit)
        result = {
            "id": str(uuid.uuid4()),
            "type": "ellipse",
            "semi_major": round(a_val, self._precision),
            "semi_minor": round(b_val, self._precision),
            "area": round(area_val, self._precision),
            "perimeter": round(perimeter_val, self._precision),
            "unit": self._unit,
            "center": (cx, cy),
            "timestamp": datetime.now().isoformat(),
        }
        self._measurements.append(result)
        return result

    def _convert(self, value, from_unit, to_unit):
        if from_unit == to_unit:
            return value
        table = self._conversion_table.get(from_unit, {})
        factor = table.get(to_unit)
        if factor is not None:
            return value * factor
        in_inches = value / table.get("in", 1) if "in" in table else value
        to_table = self._conversion_table.get("in", {})
        return in_inches * to_table.get(to_unit, 1)

    def set_grid(self, visible=True, size=20, snap=False):
        self._grid_visible = visible
        self._grid_size = max(5, min(200, size))
        self._snap_to_grid = snap

    def snap_to_grid(self, x, y):
        if not self._snap_to_grid:
            return x, y
        snapped_x = round(x / self._grid_size) * self._grid_size
        snapped_y = round(y / self._grid_size) * self._grid_size
        return snapped_x, snapped_y

    def get_measurements(self):
        return list(self._measurements)

    def clear_measurements(self):
        self._measurements.clear()

    def remove_measurement(self, measurement_id):
        self._measurements = [m for m in self._measurements if m["id"] != measurement_id]

    def export_measurements_csv(self, output_path):
        try:
            if not self._measurements:
                return {"success": False, "error": "No measurements to export"}
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Type", "Value", "Unit", "Timestamp", "Details"])
                for m in self._measurements:
                    writer.writerow([
                        m["id"], m["type"], m.get("value", ""),
                        m.get("unit", ""), m.get("timestamp", ""),
                        json.dumps({k: v for k, v in m.items() if k not in ("id", "type", "value", "unit", "timestamp")}),
                    ])
            return {"success": True, "output_path": output_path, "count": len(self._measurements)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_measurements_json(self, output_path):
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "unit": self._unit,
                    "precision": self._precision,
                    "scale_factor": self._scale_factor,
                    "measurements": self._measurements,
                }, f, indent=2)
            return {"success": True, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_supported_units(self):
        return list(self._conversion_table.keys())

    def convert_value(self, value, from_unit, to_unit):
        return round(self._convert(value, from_unit, to_unit), self._precision)
