#ifndef PDF_EDITOR_COMMON_H
#define PDF_EDITOR_COMMON_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>

#ifdef _WIN32
    #define PDF_EXPORT __declspec(dllexport)
    #define PDF_CALL __cdecl
#else
    #define PDF_EXPORT __attribute__((visibility("default")))
    #define PDF_CALL
#endif

typedef int32_t pdf_error_t;

enum {
    PDF_OK                  = 0,
    PDF_ERR_INVALID_ARG     = -1,
    PDF_ERR_FILE_NOT_FOUND  = -2,
    PDF_ERR_OUT_OF_MEMORY   = -3,
    PDF_ERR_RENDER_FAILED   = -4,
    PDF_ERR_PAGE_OUT_OF_RANGE = -5,
    PDF_ERR_ENCRYPTION_FAILED = -6,
    PDF_ERR_DECRYPTION_FAILED = -7,
    PDF_ERR_SEARCH_FAILED   = -8,
    PDF_ERR_COMPRESS_FAILED = -9,
    PDF_ERR_EXPORT_FAILED   = -10,
    PDF_ERR_OCR_FAILED      = -11,
    PDF_ERR_IO_FAILED       = -12,
    PDF_ERR_UNSUPPORTED     = -13,
    PDF_ERR_BUFFER_TOO_SMALL = -14,
    PDF_ERR_INTERNAL        = -100
};

typedef struct {
    float width;
    float height;
} pdf_page_size_t;

typedef struct {
    uint8_t *data;
    int32_t width;
    int32_t height;
    int32_t stride;
    int32_t format;
} pdf_bitmap_t;

enum {
    PDF_BITMAP_RGBA   = 0,
    PDF_BITMAP_RGB    = 1,
    PDF_BITMAP_GRAY   = 2,
    PDF_BITMAP_GRAY1  = 3
};

typedef struct {
    int32_t page_number;
    float x;
    float y;
    float width;
    float height;
} pdf_rect_t;

typedef struct {
    int32_t page;
    int32_t x;
    int32_t y;
    int32_t width;
    int32_t height;
    const char *text;
} pdf_search_result_t;

typedef struct {
    pdf_search_result_t *results;
    int32_t count;
    int32_t capacity;
} pdf_search_results_t;

typedef struct {
    char *text;
    int32_t relevance;
} pdf_suggestion_t;

typedef struct {
    pdf_suggestion_t *items;
    int32_t count;
} pdf_suggestions_t;

typedef struct {
    uint8_t *data;
    size_t size;
} pdf_buffer_t;

typedef struct {
    int32_t version_major;
    int32_t version_minor;
    int32_t is_encrypted;
    int32_t page_count;
    char *title;
    char *author;
    char *subject;
    char *creator;
    char *producer;
} pdf_metadata_t;

typedef void (*pdf_progress_callback)(float progress, void *user_data);

#define PDF_UNUSED(x) ((void)(x))

#define PDF_ALIGN(n) __attribute__((aligned(n)))

#define PDF_MIN(a, b) ((a) < (b) ? (a) : (b))
#define PDF_MAX(a, b) ((a) > (b) ? (a) : (b))
#define PDF_CLAMP(x, lo, hi) PDF_MIN(PDF_MAX((x), (lo)), (hi))

void pdf_free_buffer(pdf_buffer_t *buf);
void pdf_free_bitmap(pdf_bitmap_t *bmp);
void pdf_free_search_results(pdf_search_results_t *results);
void pdf_free_suggestions(pdf_suggestions_t *suggestions);
void pdf_free_metadata(pdf_metadata_t *meta);

const char *pdf_error_string(pdf_error_t err);

#ifdef __cplusplus
}
#endif

#endif
