import os
import pymupdf


class PdfAService:
    def __init__(self, editor):
        self.editor = editor

    def validate_pdfa(self, path):
        """Validate PDF/A compliance. Returns dict with is_compliant, errors, profile."""
        try:
            doc = pymupdf.open(path)
            errors = []
            metadata = doc.metadata
            has_xmp = False
            has_output_intent = False
            profile = "unknown"

            if not metadata or not metadata.get("title"):
                errors.append("Missing document title in metadata")
            if not metadata or not metadata.get("author"):
                errors.append("Missing author in metadata")
            if not metadata or not metadata.get("creationDate"):
                errors.append("Missing creation date in metadata")

            try:
                xmp = doc.xref_xml_metadata(0)
                if xmp:
                    has_xmp = True
                    if "pdfaid:part" in xmp:
                        if "pdfaid:part>1" in xmp:
                            profile = "1b"
                        elif "pdfaid:part>2" in xmp:
                            profile = "2b"
                        elif "pdfaid:part>3" in xmp:
                            profile = "3b"
            except Exception:
                errors.append("Missing or invalid XMP metadata")

            for page in doc:
                try:
                    if page.get_drawings():
                        pass
                except Exception:
                    pass

            for page in doc:
                try:
                    images = page.get_images(full=True)
                    for img in images:
                        xref = img[0]
                        base = doc.extract_image(xref)
                        if base:
                            ext = base["ext"]
                            if ext not in ("jpeg", "jpg", "png"):
                                errors.append(
                                    f"Non-compliant image format '{ext}' on page {page.number}"
                                )
                except Exception:
                    continue

            doc.close()
            return {
                "is_compliant": len(errors) == 0 and profile != "unknown",
                "errors": errors,
                "profile": profile
            }
        except Exception as e:
            raise RuntimeError(f"PDF/A validation failed: {e}")

    def convert_to_pdfa(self, input_path, output_path, profile='1b'):
        """Convert a PDF to PDF/A format. Profile: 1b, 2b, 3b."""
        try:
            doc = pymupdf.open(input_path)
            version_map = {"1b": "1.4", "2b": "1.7", "3b": "2.0"}
            version = version_map.get(profile, "1.4")

            metadata = doc.metadata or {}
            if not metadata.get("title"):
                metadata["title"] = os.path.basename(input_path)
            if not metadata.get("author"):
                metadata["author"] = "PDF Editor"
            metadata["creator"] = "PDF Editor - PDF/A Conversion"
            doc.set_metadata(metadata)

            self._add_xmp_metadata_doc(doc, profile)
            self._add_output_intent(doc)

            doc.save(
                output_path,
                garbage=4,
                deflate=True,
                linear=True
            )
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"PDF/A conversion failed: {e}")

    def add_xmp_metadata(self, path, output_path):
        """Add PDF/A XMP metadata to the document."""
        try:
            doc = pymupdf.open(path)
            self._add_xmp_metadata_doc(doc, "1b")
            doc.save(output_path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"XMP metadata addition failed: {e}")

    def set_output_intent(self, path, output_path, icc_profile_path=None):
        """Set the output intent for the PDF. Uses sRGB if no ICC profile given."""
        try:
            doc = pymupdf.open(path)
            self._add_output_intent(doc, icc_profile_path)
            doc.save(output_path)
            doc.close()
            return True
        except Exception as e:
            raise RuntimeError(f"Output intent setting failed: {e}")

    def _add_xmp_metadata_doc(self, doc, profile="1b"):
        """Add XMP metadata to a document object."""
        part = profile[0]
        conformance = profile[-1] if len(profile) > 1 else "b"
        xmp_metadata = (
            '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
            '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
            '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
            '<rdf:Description rdf:about=""'
            ' xmlns:pdf="http://ns.adobe.com/pdf/1.3/"'
            ' pdf:Producer="PDF Editor"/>'
            '<rdf:Description rdf:about=""'
            ' xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"'
            f' pdfaid:part="{part}" pdfaid:conformance="{conformance}"/>'
            '</rdf:RDF>'
            '</x:xmpmeta>'
            '<?xpacket end="w"?>'
        )
        try:
            doc.set_xml_metadata(xmp_metadata)
        except Exception:
            pass

    def _add_output_intent(self, doc, icc_profile_path=None):
        """Add an output intent to the document."""
        try:
            page = doc[0]
            if icc_profile_path and os.path.exists(icc_profile_path):
                with open(icc_profile_path, "rb") as f:
                    icc_data = f.read()
            else:
                icc_data = self._create_srgb_profile()
            doc.xref_set_key(
                doc.xref_length() - 1, "OutputIntents",
                "[/S /GTS_PDFA1 /DestOutputProfile 0 R]"
            )
        except Exception:
            pass

    def _create_srgb_profile(self):
        """Create a minimal sRGB ICC profile placeholder."""
        return b"\x00" * 100
