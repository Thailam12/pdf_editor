#include "common.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

void pdf_free_buffer(pdf_buffer_t *buf) {
    if (buf && buf->data) {
        free(buf->data);
        buf->data = NULL;
        buf->size = 0;
    }
}

void pdf_free_bitmap(pdf_bitmap_t *bmp) {
    if (bmp && bmp->data) {
        free(bmp->data);
        bmp->data = NULL;
        bmp->width = 0;
        bmp->height = 0;
        bmp->stride = 0;
    }
}

void pdf_free_search_results(pdf_search_results_t *results) {
    if (results) {
        if (results->results) {
            for (int32_t i = 0; i < results->count; i++) {
                if (results->results[i].text) {
                    free((void *)results->results[i].text);
                }
            }
            free(results->results);
        }
        results->results = NULL;
        results->count = 0;
        results->capacity = 0;
    }
}

void pdf_free_suggestions(pdf_suggestions_t *suggestions) {
    if (suggestions) {
        if (suggestions->items) {
            for (int32_t i = 0; i < suggestions->count; i++) {
                if (suggestions->items[i].text) {
                    free(suggestions->items[i].text);
                }
            }
            free(suggestions->items);
        }
        suggestions->items = NULL;
        suggestions->count = 0;
    }
}

void pdf_free_metadata(pdf_metadata_t *meta) {
    if (meta) {
        free(meta->title);
        free(meta->author);
        free(meta->subject);
        free(meta->creator);
        free(meta->producer);
        memset(meta, 0, sizeof(pdf_metadata_t));
    }
}

const char *pdf_error_string(pdf_error_t err) {
    switch (err) {
        case PDF_OK:                  return "Success";
        case PDF_ERR_INVALID_ARG:     return "Invalid argument";
        case PDF_ERR_FILE_NOT_FOUND:  return "File not found";
        case PDF_ERR_OUT_OF_MEMORY:   return "Out of memory";
        case PDF_ERR_RENDER_FAILED:   return "Render failed";
        case PDF_ERR_PAGE_OUT_OF_RANGE: return "Page out of range";
        case PDF_ERR_ENCRYPTION_FAILED: return "Encryption failed";
        case PDF_ERR_DECRYPTION_FAILED: return "Decryption failed";
        case PDF_ERR_SEARCH_FAILED:   return "Search failed";
        case PDF_ERR_COMPRESS_FAILED: return "Compression failed";
        case PDF_ERR_EXPORT_FAILED:   return "Export failed";
        case PDF_ERR_OCR_FAILED:      return "OCR preprocessing failed";
        case PDF_ERR_IO_FAILED:       return "I/O operation failed";
        case PDF_ERR_UNSUPPORTED:     return "Unsupported operation";
        case PDF_ERR_BUFFER_TOO_SMALL: return "Buffer too small";
        case PDF_ERR_INTERNAL:        return "Internal error";
        default:                      return "Unknown error";
    }
}
