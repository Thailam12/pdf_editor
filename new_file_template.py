import os


def create_blank_pdf(path, page_width_points=595, page_height_points=842):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=page_width_points, height=page_height_points)
    doc.save(path)
    doc.close()
    return path
