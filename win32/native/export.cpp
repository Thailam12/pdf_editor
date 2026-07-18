#include "common.h"

#include <fitz.h>
#include <mupdf/pdf.h>

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

typedef struct {
    const char *format;
    int format_id;
} format_entry_t;

static const format_entry_t supported_formats[] = {
    {"png",  0},
    {"jpg",  1},
    {"jpeg", 1},
    {"tiff", 2},
    {"tif",  2},
    {"bmp",  3},
    {NULL,   -1}
};

static int find_format(const char *format) {
    if (!format) return -1;
    for (int i = 0; supported_formats[i].format; i++) {
        if (strcmp(format, supported_formats[i].format) == 0) {
            return supported_formats[i].format_id;
        }
    }
    return -1;
}

static pdf_error_t save_pixmap_as(fz_context *ctx, fz_pixmap *pixmap,
                                   const char *path, int format_id) {
    fz_output *out = fz_new_output_to_path(ctx, path);
    if (!out) {
        return PDF_ERR_EXPORT_FAILED;
    }

    pdf_error_t result = PDF_OK;

    switch (format_id) {
        case 0: {
            fz_pixmap *rgb = NULL;
            if (pixmap->colorspace == fz_device_gray(ctx)) {
                rgb = fz_convert_pixmap(ctx, pixmap, fz_device_rgb(ctx));
                if (!rgb) {
                    result = PDF_ERR_EXPORT_FAILED;
                    break;
                }
                fz_write_pixmap_as_png(ctx, rgb, out);
                fz_drop_pixmap(ctx, rgb);
            } else {
                fz_write_pixmap_as_png(ctx, pixmap, out);
            }
            break;
        }
        case 1: {
            fz_pixmap *rgb = NULL;
            if (pixmap->colorspace == fz_device_gray(ctx)) {
                rgb = fz_convert_pixmap(ctx, pixmap, fz_device_rgb(ctx));
                if (!rgb) {
                    result = PDF_ERR_EXPORT_FAILED;
                    break;
                }
                fz_write_pixmap_as_jpeg(ctx, rgb, out, 90);
                fz_drop_pixmap(ctx, rgb);
            } else {
                fz_write_pixmap_as_jpeg(ctx, pixmap, out, 90);
            }
            break;
        }
        case 2: {
            fz_write_pixmap_as_tiff(ctx, pixmap, out);
            break;
        }
        case 3: {
            fz_write_pixmap_as_bmp(ctx, pixmap, out);
            break;
        }
        default:
            result = PDF_ERR_UNSUPPORTED;
            break;
    }

    fz_close_output(ctx, out);
    fz_drop_output(ctx, out);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL export_to_image(
    const char *pdf_path,
    int32_t page_number,
    float dpi,
    const char *format,
    const char *output_path)
{
    if (!pdf_path || !format || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    int format_id = find_format(format);
    if (format_id < 0) {
        return PDF_ERR_UNSUPPORTED;
    }

    if (dpi <= 0) dpi = 150.0f;

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

    float scale = dpi / 72.0f;
    fz_matrix ctm = fz_scale(scale, scale);

    fz_rect page_bounds;
    fz_bound_page(doc, page, &page_bounds);

    fz_irect bbox;
    fz_pixmap *pixmap = fz_new_pixmap_from_page(ctx, doc, page_number, ctm,
                                                  fz_device_rgb(ctx), 1);
    if (!pixmap) {
        fz_drop_page(ctx, page);
        fz_drop_document(ctx, doc);
        fz_drop_context(ctx);
        return PDF_ERR_RENDER_FAILED;
    }

    pdf_error_t result = save_pixmap_as(ctx, pixmap, output_path, format_id);

    fz_drop_pixmap(ctx, pixmap);
    fz_drop_page(ctx, page);
    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL export_to_image_all_pages(
    const char *pdf_path,
    float dpi,
    const char *format,
    const char *output_pattern,
    pdf_progress_callback progress,
    void *user_data)
{
    if (!pdf_path || !format || !output_pattern) {
        return PDF_ERR_INVALID_ARG;
    }

    int format_id = find_format(format);
    if (format_id < 0) {
        return PDF_ERR_UNSUPPORTED;
    }

    if (dpi <= 0) dpi = 150.0f;

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

    int page_count = fz_count_pages(doc);
    pdf_error_t result = PDF_OK;

    for (int i = 0; i < page_count; i++) {
        char path[1024];
        snprintf(path, sizeof(path), output_pattern, i);

        result = export_to_image(pdf_path, i, dpi, format, path);
        if (result != PDF_OK) {
            break;
        }

        if (progress) {
            progress((float)(i + 1) / (float)page_count, user_data);
        }
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL export_to_svg(
    const char *pdf_path,
    int32_t page_number,
    float dpi,
    const char *output_path)
{
    if (!pdf_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    if (dpi <= 0) dpi = 72.0f;

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

    fz_rect page_bounds;
    fz_bound_page(doc, page, &page_bounds);

    float scale = dpi / 72.0f;
    fz_matrix ctm = fz_scale(scale, scale);

    float width = (page_bounds.x1 - page_bounds.x0) * scale;
    float height = (page_bounds.y1 - page_bounds.y0) * scale;

    fz_device *dev = NULL;
    pdf_error_t result = PDF_OK;

    fz_output *out = fz_new_output_to_path(ctx, output_path);
    if (!out) {
        result = PDF_ERR_EXPORT_FAILED;
        goto cleanup;
    }

    fz_printf(ctx, out, "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n");
    fz_printf(ctx, out, "<svg xmlns=\"http://www.w3.org/2000/svg\" "
              "width=\"%.2f\" height=\"%.2f\" viewBox=\"0 0 %.2f %.2f\">\n",
              width, height, width, height);

    fz_printf(ctx, out, "<rect width=\"100%%\" height=\"100%%\" fill=\"white\"/>\n");

    dev = fz_new_svg_device(ctx, out, page_bounds.x0, page_bounds.y1, scale, 1, 1);

    fz_run_page(doc, page, dev, ctm, NULL);

    fz_close_device(ctx, dev);
    fz_drop_device(ctx, dev);

    fz_printf(ctx, out, "</svg>\n");

    fz_close_output(ctx, out);
    fz_drop_output(ctx, out);

cleanup:
    fz_drop_page(ctx, page);
    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL export_to_html(
    const char *pdf_path,
    const char *output_path,
    int32_t complete_document)
{
    if (!pdf_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    fz_context *ctx = fz_new_context(NULL, NULL, 512 << 20);
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
    pdf_error_t result = PDF_OK;

    FILE *f = fopen(output_path, "w");
    if (!f) {
        fz_drop_document(ctx, doc);
        fz_drop_context(ctx);
        return PDF_ERR_IO_FAILED;
    }

    if (complete_document) {
        fprintf(f, "<!DOCTYPE html>\n<html>\n<head>\n");
        fprintf(f, "<meta charset=\"UTF-8\">\n");
        fprintf(f, "<title>PDF Export</title>\n");
        fprintf(f, "<style>\n");
        fprintf(f, "body { font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }\n");
        fprintf(f, ".page { page-break-after: always; margin-bottom: 40px; }\n");
        fprintf(f, ".page-header { color: #666; font-size: 12px; border-bottom: 1px solid #ddd; margin-bottom: 10px; }\n");
        fprintf(f, "img { max-width: 100%%; height: auto; }\n");
        fprintf(f, "</style>\n</head>\n<body>\n");
    }

    for (int i = 0; i < page_count; i++) {
        fz_page *page = fz_load_page(doc, i);
        if (!page) continue;

        fz_stext_page *stext = fz_new_stext_page_from_page(ctx, page, NULL);
        if (!stext) {
            fz_drop_page(ctx, page);
            continue;
        }

        if (complete_document) {
            fprintf(f, "<div class=\"page\" id=\"page-%d\">\n", i + 1);
            fprintf(f, "<div class=\"page-header\">Page %d of %d</div>\n", i + 1, page_count);
        } else {
            fprintf(f, "<div class=\"page\">\n");
        }

        for (fz_block *block = stext->first_block; block; block = block->next) {
            if (block->type == FZ_STEXT_BLOCK_TEXT) {
                for (fz_line *line = block->u.t.first_line; line; line = line->next) {
                    int font_size = 12;
                    int is_bold = 0;

                    if (line->first_span && line->first_span->flags) {
                        float size = line->first_span->size;
                        font_size = (int)(size + 0.5f);
                        if (line->first_span->flags & 1) is_bold = 1;
                    }

                    fprintf(f, "<p style=\"font-size: %dpx", font_size);
                    if (is_bold) fprintf(f, "; font-weight: bold");
                    fprintf(f, "\">");

                    for (fz_span *span = line->first_span; span; span = span->next) {
                        if (span->text && strlen(span->text) > 0) {
                            char *escaped = NULL;
                            size_t text_len = strlen(span->text);

                            escaped = (char *)malloc(text_len * 6 + 1);
                            if (escaped) {
                                size_t j = 0;
                                for (size_t k = 0; k < text_len; k++) {
                                    char c = span->text[k];
                                    switch (c) {
                                        case '&':  escaped[j++] = '&'; escaped[j++] = 'a'; escaped[j++] = 'm'; escaped[j++] = 'p'; escaped[j++] = ';'; break;
                                        case '<':  escaped[j++] = '&'; escaped[j++] = 'l'; escaped[j++] = 't'; escaped[j++] = ';'; break;
                                        case '>':  escaped[j++] = '&'; escaped[j++] = 'g'; escaped[j++] = 't'; escaped[j++] = ';'; break;
                                        case '"':  escaped[j++] = '&'; escaped[j++] = 'q'; escaped[j++] = 'u'; escaped[j++] = 'o'; escaped[j++] = 't'; escaped[j++] = ';'; break;
                                        default:   escaped[j++] = c; break;
                                    }
                                }
                                escaped[j] = '\0';
                                fprintf(f, "%s", escaped);
                                free(escaped);
                            } else {
                                fprintf(f, "%s", span->text);
                            }
                        }
                    }

                    fprintf(f, "</p>\n");
                }
            }
        }

        fprintf(f, "</div>\n");

        fz_drop_stext_page(ctx, stext);
        fz_drop_page(ctx, page);
    }

    if (complete_document) {
        fprintf(f, "</body>\n</html>\n");
    }

    fclose(f);

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL export_pages_to_images(
    const char *pdf_path,
    int32_t start_page,
    int32_t end_page,
    float dpi,
    const char *format,
    const char *output_dir,
    const char *name_prefix,
    pdf_progress_callback progress,
    void *user_data)
{
    if (!pdf_path || !format || !output_dir || !name_prefix) {
        return PDF_ERR_INVALID_ARG;
    }

    int format_id = find_format(format);
    if (format_id < 0) {
        return PDF_ERR_UNSUPPORTED;
    }

    if (dpi <= 0) dpi = 150.0f;
    if (end_page < start_page) end_page = start_page;

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

    int page_count = fz_count_pages(doc);
    if (start_page < 0) start_page = 0;
    if (end_page >= page_count) end_page = page_count - 1;

    pdf_error_t result = PDF_OK;

    for (int i = start_page; i <= end_page; i++) {
        char path[2048];
        const char *ext = format;
        if (format_id == 1) ext = "jpg";
        else if (format_id == 2) ext = "tiff";
        else if (format_id == 3) ext = "bmp";

        snprintf(path, sizeof(path), "%s/%s_%04d.%s", output_dir, name_prefix, i, ext);

        result = export_to_image(pdf_path, i, dpi, format, path);
        if (result != PDF_OK) {
            break;
        }

        if (progress) {
            float p = (float)(i - start_page + 1) / (float)(end_page - start_page + 1);
            progress(p, user_data);
        }
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL export_to_multipage_tiff(
    const char *pdf_path,
    float dpi,
    const char *output_path)
{
    if (!pdf_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    if (dpi <= 0) dpi = 150.0f;

    fz_context *ctx = fz_new_context(NULL, NULL, 512 << 20);
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
    pdf_error_t result = PDF_OK;

    for (int i = 0; i < page_count; i++) {
        float scale = dpi / 72.0f;
        fz_matrix ctm = fz_scale(scale, scale);

        fz_pixmap *pixmap = fz_new_pixmap_from_page(ctx, doc, i, ctm,
                                                      fz_device_rgb(ctx), 1);
        if (!pixmap) {
            continue;
        }

        char page_path[1024];
        snprintf(page_path, sizeof(page_path), "%s_page_%d.tiff", output_path, i);

        fz_output *out = fz_new_output_to_path(ctx, page_path);
        if (out) {
            fz_write_pixmap_as_tiff(ctx, pixmap, out);
            fz_close_output(ctx, out);
            fz_drop_output(ctx, out);
        }

        fz_drop_pixmap(ctx, pixmap);
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}
