import os
import pymupdf


class CompressService:
    def __init__(self, editor):
        self.editor = editor

    def compress(self, input_path, output_path, level='medium'):
        """Compress a PDF file. Level: low, medium, high."""
        try:
            quality_map = {'low': 30, 'medium': 60, 'high': 80}
            quality = quality_map.get(level, 60)
            doc = pymupdf.open(input_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                images = page.get_images(full=True)
                for img_index in images:
                    xref = img_index[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            ext = base_image["ext"]
                            if ext in ("png", "jpeg", "jpg"):
                                from PIL import Image as PILImage
                                import io
                                pil_img = PILImage.open(io.BytesIO(image_bytes))
                                if pil_img.mode == "RGBA":
                                    pil_img = pil_img.convert("RGB")
                                buf = io.BytesIO()
                                pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
                                doc.update_stream(xref, buf.getvalue())
                    except Exception:
                        continue
            if os.path.abspath(input_path) == os.path.abspath(output_path):
                import tempfile
                directory = os.path.dirname(output_path)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', dir=directory) as tmp:
                    temp_path = tmp.name
                doc.save(temp_path)
                doc.close()
                os.replace(temp_path, output_path)
            else:
                doc.save(output_path)
                doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Compression failed: {e}")

    def get_compression_info(self, path):
        """Return dict with file_size, page_count, image_count, estimated_savings."""
        try:
            file_size = os.path.getsize(path)
            doc = pymupdf.open(path)
            page_count = len(doc)
            image_count = 0
            for page in doc:
                image_count += len(page.get_images(full=True))
            doc.close()
            estimated_savings = int(file_size * 0.15)
            return {
                "file_size": file_size,
                "page_count": page_count,
                "image_count": image_count,
                "estimated_savings": estimated_savings
            }
        except Exception as e:
            raise RuntimeError(f"Cannot get compression info: {e}")

    def optimize_images(self, path, quality):
        """Optimize images in the PDF with given JPEG quality (1-100)."""
        try:
            doc = pymupdf.open(path)
            for page in doc:
                images = page.get_images(full=True)
                for img_info in images:
                    xref = img_info[0]
                    try:
                        base_image = doc.extract_image(xref)
                        if base_image:
                            import io
                            from PIL import Image as PILImage
                            pil_img = PILImage.open(io.BytesIO(base_image["image"]))
                            if pil_img.mode == "RGBA":
                                pil_img = pil_img.convert("RGB")
                            buf = io.BytesIO()
                            pil_img.save(buf, format="JPEG", quality=quality, optimize=True)
                            doc.update_stream(xref, buf.getvalue())
                    except Exception:
                        continue
            doc.save(path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Image optimization failed: {e}")

    def linearize(self, path, output_path):
        """Linearize a PDF for fast web display."""
        try:
            doc = pymupdf.open(path)
            doc.save(output_path, garbage=3, deflate=True, linear=True)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Linearization failed: {e}")

    def remove_metadata(self, path, output_path):
        """Remove metadata from a PDF."""
        try:
            doc = pymupdf.open(path)
            doc.set_metadata({})
            doc.save(output_path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Metadata removal failed: {e}")

    def flatten_annotations(self, path, output_path):
        """Flatten annotations so they become part of the page content."""
        try:
            doc = pymupdf.open(path)
            for page in doc:
                annots = list(page.annots()) if page.annots() else []
                for annot in annots:
                    try:
                        annot.flatten()
                    except Exception:
                        continue
            doc.save(output_path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Annotation flattening failed: {e}")
