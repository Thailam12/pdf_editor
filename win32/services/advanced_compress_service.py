import os
import io
import zlib
import hashlib
import struct

import pymupdf


COMPRESSION_LEVELS = {
    "low": {"deflate_level": 1, "image_quality": 90, "dpi": 300, "subset_fonts": False},
    "medium": {"deflate_level": 6, "image_quality": 75, "dpi": 150, "subset_fonts": True},
    "high": {"deflate_level": 9, "image_quality": 50, "dpi": 150, "subset_fonts": True},
    "max": {"deflate_level": 9, "image_quality": 30, "dpi": 72, "subset_fonts": True},
}


class AdvancedCompressService:
    def __init__(self, editor):
        self.editor = editor

    def compress(self, input_path, output_path, level="medium", options=None):
        opts = COMPRESSION_LEVELS.get(level, COMPRESSION_LEVELS["medium"])
        if options:
            opts.update(options)

        try:
            doc = pymupdf.open(input_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        original_size = os.path.getsize(input_path)

        self._recompress_images(doc, opts)
        self._remove_unused_objects(doc)
        self._remove_duplicates(doc)

        if opts.get("subset_fonts"):
            self._subset_fonts(doc)

        garbage_level = 4 if level in ("high", "max") else 3
        try:
            doc.save(output_path, garbage=garbage_level, deflate=True, clean=True, linear=opts.get("linear", False))
        except Exception as e:
            doc.close()
            return {"success": False, "error": str(e)}

        doc.close()

        new_size = os.path.getsize(output_path)
        ratio = (1 - new_size / original_size) * 100 if original_size > 0 else 0

        return {
            "success": True,
            "output_path": output_path,
            "original_size": original_size,
            "compressed_size": new_size,
            "ratio": round(ratio, 1),
            "level": level,
            "saved_bytes": original_size - new_size,
        }

    def _recompress_images(self, doc, opts):
        quality = opts.get("image_quality", 75)
        target_dpi = opts.get("dpi", 150)
        for page in doc:
            try:
                images = page.get_images(full=True)
                for img in images:
                    xref = img[0]
                    try:
                        img_data = doc.extract_image(xref)
                        if not img_data or "image" not in img_data:
                            continue
                        img_bytes = img_data["image"]
                        ext = img_data.get("ext", "png")
                        width = img_data.get("width", 0)
                        height = img_data.get("height", 0)

                        if ext in ("jpeg", "jpg"):
                            if quality < 90:
                                recompressed = self._recompress_jpeg(img_bytes, quality)
                                if recompressed and len(recompressed) < len(img_bytes):
                                    doc.update_stream(xref, recompressed)
                        elif ext == "png":
                            if target_dpi < 300 and width > 0 and height > 0:
                                scale = target_dpi / 300.0
                                if scale < 1.0:
                                    new_w = int(width * scale)
                                    new_h = int(height * scale)
                                    png_data = self._downsample_png(img_bytes, new_w, new_h)
                                    if png_data and len(png_data) < len(img_bytes):
                                        doc.update_stream(xref, png_data)
                    except Exception:
                        continue
            except Exception:
                continue

    def _recompress_jpeg(self, img_bytes, quality):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            return buf.getvalue()
        except Exception:
            return None

    def _downsample_png(self, img_bytes, new_width, new_height):
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes))
            img = img.resize((new_width, new_height), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
        except Exception:
            return None

    def _remove_unused_objects(self, doc):
        try:
            xref_count = doc.xref_length()
            referenced_xrefs = set()
            for pg in range(len(doc)):
                page = doc[pg]
                try:
                    xref = page.xref
                    referenced_xrefs.add(xref)
                except Exception:
                    pass
        except Exception:
            pass

    def _remove_duplicates(self, doc):
        stream_hashes = {}
        for pg in range(len(doc)):
            try:
                page = doc[pg]
                for img in page.get_images(full=True):
                    xref = img[0]
                    try:
                        img_data = doc.extract_image(xref)
                        if img_data and "image" in img_data:
                            h = hashlib.md5(img_data["image"]).hexdigest()
                            if h in stream_hashes:
                                pass
                            else:
                                stream_hashes[h] = xref
                    except Exception:
                        pass
            except Exception:
                pass

    def _subset_fonts(self, doc):
        try:
            for pg in range(len(doc)):
                page = doc[pg]
                try:
                    page.clean_contents()
                except Exception:
                    pass
        except Exception:
            pass

    def estimate_size(self, input_path, level="medium"):
        opts = COMPRESSION_LEVELS.get(level, COMPRESSION_LEVELS["medium"])
        try:
            original_size = os.path.getsize(input_path)
            doc = pymupdf.open(input_path)
            image_count = 0
            total_image_bytes = 0
            for page in doc:
                try:
                    images = page.get_images(full=True)
                    image_count += len(images)
                    for img in images:
                        try:
                            img_data = doc.extract_image(img[0])
                            if img_data and "image" in img_data:
                                total_image_bytes += len(img_data["image"])
                        except Exception:
                            pass
                except Exception:
                    pass
            text_ratio = (original_size - total_image_bytes) / original_size if original_size > 0 else 0.5
            quality = opts.get("image_quality", 75)
            image_compression_ratio = quality / 100.0
            estimated_image = int(total_image_bytes * image_compression_ratio)
            estimated_text = int(original_size * text_ratio * 0.85)
            estimated = estimated_image + estimated_text
            doc.close()
            return {
                "original_size": original_size,
                "estimated_size": estimated,
                "estimated_ratio": round((1 - estimated / original_size) * 100, 1) if original_size > 0 else 0,
                "image_count": image_count,
                "level": level,
            }
        except Exception as e:
            return {"error": str(e)}

    def linearize(self, input_path, output_path):
        try:
            doc = pymupdf.open(input_path)
            doc.save(output_path, garbage=4, deflate=True, clean=True, linear=True)
            doc.close()
            return {"success": True, "output_path": output_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_compression_levels(self):
        return {k: {"deflate_level": v["deflate_level"], "image_quality": v["image_quality"], "dpi": v["dpi"]} for k, v in COMPRESSION_LEVELS.items()}

    def compare_quality(self, input_path, output_dir=None):
        if not output_dir:
            output_dir = os.path.join(os.path.dirname(input_path), "compression_compare")
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        original_size = os.path.getsize(input_path)
        for level in COMPRESSION_LEVELS:
            out_path = os.path.join(output_dir, f"compressed_{level}.pdf")
            result = self.compress(input_path, out_path, level=level)
            if result.get("success"):
                results[level] = {
                    "path": out_path,
                    "size": result["compressed_size"],
                    "ratio": result["ratio"],
                }
        results["original"] = {"size": original_size}
        return results
