#include "common.h"

#include <fitz.h>
#include <mupdf/pdf.h>

#include <stdlib.h>
#include <string.h>

typedef struct {
    fz_context *ctx;
    fz_document *doc;
    char *path;
} pdf_compressor_handle;

static char *duplicate_string(const char *src) {
    if (!src) return NULL;
    size_t len = strlen(src);
    char *dup = (char *)malloc(len + 1);
    if (dup) {
        memcpy(dup, src, len + 1);
    }
    return dup;
}

PDF_EXPORT pdf_error_t PDF_CALL compress_pdf(
    const char *input_path,
    const char *output_path,
    int32_t quality,
    pdf_progress_callback progress,
    void *user_data)
{
    if (!input_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    if (quality < 0) quality = 0;
    if (quality > 100) quality = 100;

    fz_context *ctx = fz_new_context(NULL, NULL, 512 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    pdf_error_t result = PDF_OK;
    fz_document *doc = NULL;
    fz_write_options opts;
    memset(&opts, 0, sizeof(opts));
    opts.do_garbage = 1;
    opts.do_deflate = 1;
    opts.do_linear = 0;
    opts.do_clean = 1;
    opts.do_pretty = 0;

    doc = fz_open_document(ctx, input_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    int page_count = fz_count_pages(doc);

    if (progress) {
        progress(0.0f, user_data);
    }

    for (int i = 0; i < page_count; i++) {
        fz_page *page = fz_load_page(doc, i);
        if (!page) continue;

        fz_stext_page *stext = fz_new_stext_page_from_page(ctx, page, NULL);
        if (stext) {
            fz_drop_stext_page(ctx, stext);
        }

        fz_drop_page(ctx, page);

        if (progress) {
            progress((float)(i + 1) / (float)page_count * 0.5f, user_data);
        }
    }

    if (progress) {
        progress(0.5f, user_data);
    }

    fz_save_document(ctx, doc, output_path, &opts);

    if (progress) {
        progress(1.0f, user_data);
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL optimize_images(
    const char *input_path,
    const char *output_path,
    int32_t max_width,
    int32_t max_height,
    int32_t jpeg_quality)
{
    if (!input_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    if (jpeg_quality < 1) jpeg_quality = 1;
    if (jpeg_quality > 100) jpeg_quality = 100;
    if (max_width <= 0) max_width = 2048;
    if (max_height <= 0) max_height = 2048;

    fz_context *ctx = fz_new_context(NULL, NULL, 512 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, input_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    int page_count = fz_count_pages(doc);

    for (int i = 0; i < page_count; i++) {
        fz_page *page = fz_load_page(doc, i);
        if (!page) continue;

        fz_rect page_rect;
        fz_bound_page(doc, page, &page_rect);

        fz_drop_page(ctx, page);
    }

    pdf_error_t result = PDF_OK;
    fz_write_options opts;
    memset(&opts, 0, sizeof(opts));
    opts.do_garbage = 1;
    opts.do_deflate = 1;
    opts.do_clean = 1;

    if (fz_save_document(ctx, doc, output_path, &opts) != PDF_OK) {
        result = PDF_ERR_COMPRESS_FAILED;
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL linearize_pdf(
    const char *input_path,
    const char *output_path)
{
    if (!input_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    fz_context *ctx = fz_new_context(NULL, NULL, 512 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    fz_document *doc = fz_open_document(ctx, input_path);
    if (!doc) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    fz_write_options opts;
    memset(&opts, 0, sizeof(opts));
    opts.do_linear = 1;
    opts.do_garbage = 1;
    opts.do_deflate = 1;
    opts.do_clean = 1;

    pdf_error_t result = PDF_OK;

    if (fz_save_document(ctx, doc, output_path, &opts) != PDF_OK) {
        result = PDF_ERR_COMPRESS_FAILED;
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL flatten_annotations(
    const char *input_path,
    const char *output_path,
    int32_t flatten_all)
{
    if (!input_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    fz_context *ctx = fz_new_context(NULL, NULL, 512 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    pdf_obj *impl = NULL;
    pdf_obj *type = NULL;
    pdf_obj *subtypes = NULL;
    pdf_obj *mark_info = NULL;
    pdf_obj *flags = NULL;

    pdf_document *pdf = pdf_open_document(ctx, input_path);
    if (!pdf) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    int page_count = pdf_count_pages(ctx, pdf);

    for (int i = 0; i < page_count; i++) {
        pdf_page *page = pdf_load_page(ctx, pdf, i);
        if (!page) continue;

        pdf_obj *page_obj = pdf_page_obj(ctx, page);

        pdf_obj *annots = pdf_dict_get(ctx, page_obj, PDF_NAME(Annots));
        if (annots && pdf_is_array(ctx, annots)) {
            int annot_count = pdf_array_len(ctx, annots);

            for (int j = annot_count - 1; j >= 0; j--) {
                pdf_obj *annot = pdf_array_get(ctx, annots, j);
                if (!annot) continue;

                pdf_obj *subtype = pdf_dict_get(ctx, annot, PDF_NAME(Subtype));
                if (!subtype) continue;

                int should_flatten = flatten_all ||
                    pdf_name_eq(ctx, subtype, PDF_NAME(Widget)) ||
                    pdf_name_eq(ctx, subtype, PDF_NAME(Link)) ||
                    pdf_name_eq(ctx, subtype, PDF_NAME(Text)) ||
                    pdf_name_eq(ctx, subtype, PDF_NAME(Line)) ||
                    pdf_name_eq(ctx, subtype, PDF_NAME(Square)) ||
                    pdf_name_eq(ctx, subtype, PDF_NAME(Circle));

                if (should_flatten) {
                    pdf_dict_del(ctx, annot, PDF_NAME(A));
                    pdf_dict_del(ctx, annot, PDF_NAME(C));
                    pdf_dict_del(ctx, annot, PDF_NAME(BS));
                    pdf_dict_del(ctx, annot, PDF_NAME Border));
                }
            }
        }

        pdf_drop_page(ctx, page);
    }

    pdf_write_options wopts;
    memset(&wopts, 0, sizeof(wopts));
    wopts.do_incremental = 0;
    wopts.do_deflate = 1;
    wopts.do_clean = 1;
    wopts.do_garbage = 1;

    pdf_save_document(ctx, pdf, output_path, &wopts);

    pdf_drop_document(ctx, pdf);
    fz_drop_context(ctx);

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL remove_metadata(
    const char *input_path,
    const char *output_path,
    int32_t keep_producer)
{
    if (!input_path || !output_path) {
        return PDF_ERR_INVALID_ARG;
    }

    fz_context *ctx = fz_new_context(NULL, NULL, 256 << 20);
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    fz_register_document_handlers(ctx);

    pdf_document *pdf = pdf_open_document(ctx, input_path);
    if (!pdf) {
        fz_drop_context(ctx);
        return PDF_ERR_FILE_NOT_FOUND;
    }

    pdf_obj *trailer = pdf_trailer(ctx, pdf);
    if (!trailer) {
        fz_drop_context(ctx);
        return PDF_ERR_INTERNAL;
    }

    pdf_obj *info = pdf_dict_get(ctx, trailer, PDF_NAME(Info));
    if (info && pdf_is_dict(ctx, info)) {
        pdf_dict_del(ctx, info, PDF_NAME(Title));
        pdf_dict_del(ctx, info, PDF_NAME(Author));
        pdf_dict_del(ctx, info, PDF_NAME(Subject));
        pdf_dict_del(ctx, info, PDF_NAME(Keywords));
        pdf_dict_del(ctx, info, PDF_NAME(Creator));
        pdf_dict_del(ctx, info, PDF_NAME(Producer));
        pdf_dict_del(ctx, info, PDF_NAME(CreationDate));
        pdf_dict_del(ctx, info, PDF_NAME(ModDate));
    }

    pdf_obj *xmp = pdf_dict_get(ctx, trailer, PDF_NAME(Metadata));
    if (xmp) {
        pdf_dict_del(ctx, trailer, PDF_NAME(Metadata));
    }

    pdf_write_options opts;
    memset(&opts, 0, sizeof(opts));
    opts.do_garbage = 1;
    opts.do_deflate = 1;
    opts.do_clean = 1;

    pdf_save_document(ctx, pdf, output_path, &opts);

    pdf_drop_document(ctx, pdf);
    fz_drop_context(ctx);

    return PDF_OK;
}

PDF_EXPORT int32_t PDF_CALL pdf_compress_get_version(void) {
    return 1;
}
