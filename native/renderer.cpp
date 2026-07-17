#include "common.h"

#include <fitz.h>
#include <mupdf/pdf.h>

#include <stdlib.h>
#include <string.h>
#include <math.h>

typedef struct {
    fz_context *ctx;
    fz_document *doc;
} pdf_renderer_handle;

static int calculate_stride(int width, int format) {
    int bytes_per_pixel;
    switch (format) {
        case PDF_BITMAP_RGBA:  bytes_per_pixel = 4; break;
        case PDF_BITMAP_RGB:   bytes_per_pixel = 3; break;
        case PDF_BITMAP_GRAY:  bytes_per_pixel = 1; break;
        case PDF_BITMAP_GRAY1: bytes_per_pixel = 1; break;
        default:               bytes_per_pixel = 4; break;
    }
    int stride = width * bytes_per_pixel;
    stride = (stride + 3) & ~3;
    return stride;
}

static fz_pixmap *create_fz_pixmap(fz_context *ctx, int width, int height, int format) {
    fz_colorspace *cs;
    int n;

    switch (format) {
        case PDF_BITMAP_RGBA:
            cs = fz_device_rgb(ctx);
            n = 4;
            break;
        case PDF_BITMAP_RGB:
            cs = fz_device_rgb(ctx);
            n = 3;
            break;
        case PDF_BITMAP_GRAY:
        case PDF_BITMAP_GRAY1:
            cs = fz_device_gray(ctx);
            n = 1;
            break;
        default:
            cs = fz_device_rgb(ctx);
            n = 4;
            break;
    }

    return fz_new_pixmap(ctx, cs, width, height, NULL, 1);
}

static pdf_error_t render_page_internal(fz_context *ctx, fz_document *doc,
                                         int page_num, float zoom,
                                         pdf_bitmap_t *out_bitmap,
                                         int x_rect, int y_rect,
                                         int w_rect, int h_rect) {
    if (!ctx || !doc || !out_bitmap) {
        return PDF_ERR_INVALID_ARG;
    }

    int page_count = fz_count_pages(doc);
    if (page_num < 0 || page_num >= page_count) {
        return PDF_ERR_PAGE_OUT_OF_RANGE;
    }

    fz_page *page = NULL;
    fz_pixmap *pixmap = NULL;
    fz_device *dev = NULL;
    fz_matrix ctm;
    fz_rect rect;
    pdf_error_t result = PDF_OK;

    page = fz_load_page(doc, page_num);
    if (!page) {
        return PDF_ERR_RENDER_FAILED;
    }

    fz_rect page_bounds;
    fz_bound_page(doc, page, &page_bounds);

    float scale = zoom / 100.0f;
    ctm = fz_scale(scale, scale);

    if (w_rect > 0 && h_rect > 0) {
        rect.x0 = (float)x_rect;
        rect.y0 = (float)y_rect;
        rect.x1 = (float)(x_rect + w_rect);
        rect.y1 = (float)(y_rect + h_rect);
    } else {
        rect = page_bounds;
    }

    int pix_width = (int)ceilf((rect.x1 - rect.x0) * scale);
    int pix_height = (int)ceilf((rect.y1 - rect.y0) * scale);

    if (pix_width <= 0 || pix_height <= 0) {
        fz_drop_page(ctx, page);
        return PDF_ERR_RENDER_FAILED;
    }

    pixmap = create_fz_pixmap(ctx, pix_width, pix_height, out_bitmap->format);
    if (!pixmap) {
        fz_drop_page(ctx, page);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_clear_pixmap(ctx, pixmap, 0xFF);

    dev = fz_new_draw_device(ctx, ctm, pixmap);
    if (!dev) {
        fz_drop_pixmap(ctx, pixmap);
        fz_drop_page(ctx, page);
        return PDF_ERR_RENDER_FAILED;
    }

    fz_run_page(doc, page, dev, fz_identity, NULL);

    fz_close_device(ctx, dev);
    fz_drop_device(ctx, dev);

    int stride = calculate_stride(pix_width, out_bitmap->format);
    size_t buf_size = (size_t)stride * pix_height;
    uint8_t *buf = (uint8_t *)malloc(buf_size);
    if (!buf) {
        fz_drop_pixmap(ctx, pixmap);
        fz_drop_page(ctx, page);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    unsigned char *samples = fz_pixmap_samples(ctx, pixmap);
    int src_stride = pixmap->stride;

    for (int y = 0; y < pix_height; y++) {
        memcpy(buf + (size_t)y * stride,
               samples + (size_t)y * src_stride,
               (size_t)pix_width * (out_bitmap->format == PDF_BITMAP_RGBA ? 4 :
                                    out_bitmap->format == PDF_BITMAP_RGB ? 3 : 1));
    }

    out_bitmap->data = buf;
    out_bitmap->width = pix_width;
    out_bitmap->height = pix_height;
    out_bitmap->stride = stride;

    fz_drop_pixmap(ctx, pixmap);
    fz_drop_page(ctx, page);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL render_page_to_bitmap(
    const char *pdf_path,
    int32_t page_number,
    float zoom,
    int32_t format,
    pdf_bitmap_t *out_bitmap)
{
    if (!pdf_path || !out_bitmap) {
        return PDF_ERR_INVALID_ARG;
    }
    if (zoom <= 0) zoom = 100.0f;

    fz_context *ctx = fz_new_context(NULL, NULL, 256 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, pdf_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    pdf_error_t err = render_page_internal(ctx, doc, page_number, zoom,
                                            out_bitmap, 0, 0, 0, 0);

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return err;
}

PDF_EXPORT pdf_error_t PDF_CALL get_page_size(
    const char *pdf_path,
    int32_t page_number,
    pdf_page_size_t *out_size)
{
    if (!pdf_path || !out_size) {
        return PDF_ERR_INVALID_ARG;
    }

    fz_context *ctx = fz_new_context(NULL, NULL, 64 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, pdf_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    int page_count = fz_count_pages(doc);
    if (page_number < 0 || page_number >= page_count) {
        fz_drop_document(ctx, doc);
        fz_drop_context(ctx);
        return PDF_ERR_PAGE_OUT_OF_RANGE;
    }

    fz_page *page = fz_load_page(doc, page_number);
    if (!page) {
        fz_drop_document(ctx, doc);
        fz_drop_context(ctx);
        return PDF_ERR_RENDER_FAILED;
    }

    fz_rect bounds;
    fz_bound_page(doc, page, &bounds);

    out_size->width = bounds.x1 - bounds.x0;
    out_size->height = bounds.y1 - bounds.y0;

    fz_drop_page(ctx, page);
    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL get_page_count(
    const char *pdf_path,
    int32_t *out_count)
{
    if (!pdf_path || !out_count) {
        return PDF_ERR_INVALID_ARG;
    }

    fz_context *ctx = fz_new_context(NULL, NULL, 64 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, pdf_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    *out_count = fz_count_pages(doc);

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL render_page_region(
    const char *pdf_path,
    int32_t page_number,
    float zoom,
    int32_t format,
    const pdf_rect_t *region,
    pdf_bitmap_t *out_bitmap)
{
    if (!pdf_path || !out_bitmap || !region) {
        return PDF_ERR_INVALID_ARG;
    }
    if (zoom <= 0) zoom = 100.0f;

    fz_context *ctx = fz_new_context(NULL, NULL, 256 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, pdf_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    pdf_error_t err = render_page_internal(ctx, doc, page_number, zoom,
                                            out_bitmap,
                                            (int)region->x, (int)region->y,
                                            (int)region->width, (int)region->height);

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return err;
}
