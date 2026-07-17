#include "common.h"

#include <fitz.h>
#include <mupdf/pdf.h>

#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <stdio.h>

#define MAX_SEARCH_HITS 4096
#define MAX_SUGGESTIONS 64
#define INITIAL_INDEX_CAPACITY 1024

typedef struct {
    char *text;
    int32_t page;
    int32_t char_offset;
    int32_t length;
} indexed_text_t;

typedef struct {
    indexed_text_t *entries;
    int32_t count;
    int32_t capacity;
} text_index_t;

static char *duplicate_string(const char *src) {
    if (!src) return NULL;
    size_t len = strlen(src);
    char *dup = (char *)malloc(len + 1);
    if (dup) {
        memcpy(dup, src, len + 1);
    }
    return dup;
}

static char *to_lowercase(const char *src) {
    if (!src) return NULL;
    size_t len = strlen(src);
    char *lower = (char *)malloc(len + 1);
    if (!lower) return NULL;

    for (size_t i = 0; i < len; i++) {
        lower[i] = (char)tolower((unsigned char)src[i]);
    }
    lower[len] = '\0';
    return lower;
}

static int boyer_moore_horspool_last(const unsigned char *pattern, int pat_len, int last[256]) {
    for (int i = 0; i < 256; i++) {
        last[i] = pat_len;
    }
    for (int i = 0; i < pat_len - 1; i++) {
        last[pattern[i]] = pat_len - 1 - i;
    }
    return 0;
}

static int boyer_moore_horspool_search(const unsigned char *text, int text_len,
                                         const unsigned char *pattern, int pat_len,
                                         int last[256]) {
    if (pat_len > text_len) return -1;
    if (pat_len == 0) return 0;

    int i = pat_len - 1;
    while (i < text_len) {
        int j = pat_len - 1;
        int k = i;
        while (j >= 0 && text[k] == pattern[j]) {
            k--;
            j--;
        }
        if (j < 0) return k + 1;
        i += last[text[i]];
    }
    return -1;
}

static void index_page_text(fz_context *ctx, fz_document *doc, int page_num, text_index_t *index) {
    fz_page *page = fz_load_page(doc, page_num);
    if (!page) return;

    fz_stext_page *stext = fz_new_stext_page_from_page(ctx, page, NULL);
    if (!stext) {
        fz_drop_page(ctx, page);
        return;
    }

    fz_buffer *buf = fz_new_buffer(ctx, 1024);
    fz_document *doc_ref = doc;

    for (fz_block *block = stext->first_block; block; block = block->next) {
        if (block->type != FZ_STEXT_BLOCK_TEXT) continue;

        for (fz_line *line = block->u.t.first_line; line; line = line->next) {
            for (fz_span *span = line->first_span; span; span = span->next) {
                const char *text = (const char *)span->text;
                if (!text || strlen(text) == 0) continue;

                if (index->count >= index->capacity) {
                    int32_t new_cap = index->capacity ? index->capacity * 2 : INITIAL_INDEX_CAPACITY;
                    indexed_text_t *new_entries = (indexed_text_t *)realloc(
                        index->entries, (size_t)new_cap * sizeof(indexed_text_t));
                    if (!new_entries) continue;
                    index->entries = new_entries;
                    index->capacity = new_cap;
                }

                indexed_text_t *entry = &index->entries[index->count];
                entry->text = duplicate_string(text);
                entry->page = page_num;
                entry->char_offset = 0;
                entry->length = (int32_t)strlen(text);

                if (entry->text) {
                    index->count++;
                }
            }
        }
    }

    fz_drop_buffer(ctx, buf);
    fz_drop_stext_page(ctx, stext);
    fz_drop_page(ctx, page);
}

PDF_EXPORT pdf_error_t PDF_CALL index_document(
    const char *pdf_path,
    void **out_handle)
{
    if (!pdf_path || !out_handle) {
        return PDF_ERR_INVALID_ARG;
    }

    *out_handle = NULL;

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

    text_index_t *index = (text_index_t *)calloc(1, sizeof(text_index_t));
    if (!index) {
        fz_drop_document(ctx, doc);
        fz_drop_context(ctx);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    int page_count = fz_count_pages(doc);
    for (int i = 0; i < page_count; i++) {
        index_page_text(ctx, doc, i, index);
    }

    fz_drop_document(ctx, doc);
    fz_drop_context(ctx);

    *out_handle = index;
    return PDF_OK;
}

PDF_EXPORT void PDF_CALL free_index(void *handle) {
    if (!handle) return;

    text_index_t *index = (text_index_t *)handle;
    if (index->entries) {
        for (int32_t i = 0; i < index->count; i++) {
            free(index->entries[i].text);
        }
        free(index->entries);
    }
    free(index);
}

PDF_EXPORT pdf_error_t PDF_CALL search_text(
    void *handle,
    const char *query,
    int32_t case_sensitive,
    int32_t whole_word,
    int32_t use_regex,
    pdf_search_results_t *out_results)
{
    if (!handle || !query || !out_results) {
        return PDF_ERR_INVALID_ARG;
    }

    text_index_t *index = (text_index_t *)handle;
    out_results->results = NULL;
    out_results->count = 0;
    out_results->capacity = 0;

    if (index->count == 0) {
        return PDF_OK;
    }

    out_results->results = (pdf_search_result_t *)calloc((size_t)MAX_SEARCH_HITS,
                                                          sizeof(pdf_search_result_t));
    if (!out_results->results) {
        return PDF_ERR_OUT_OF_MEMORY;
    }
    out_results->capacity = MAX_SEARCH_HITS;

    char *query_lower = case_sensitive ? duplicate_string(query) : to_lowercase(query);
    if (!query_lower) {
        free(out_results->results);
        out_results->results = NULL;
        return PDF_ERR_OUT_OF_MEMORY;
    }

    int query_len = (int)strlen(query_lower);

    int last[256];
    boyer_moore_horspool_last((const unsigned char *)query_lower, query_len, last);

    int32_t hit_count = 0;

    for (int32_t i = 0; i < index->count && hit_count < MAX_SEARCH_HITS; i++) {
        indexed_text_t *entry = &index->entries[i];
        if (!entry->text || entry->length == 0) continue;

        char *entry_lower = case_sensitive ? NULL : to_lowercase(entry->text);
        const char *search_text = case_sensitive ? entry->text : entry_lower;

        if (!search_text) continue;

        int search_len = entry->length;
        int pos = 0;

        while (pos <= search_len - query_len && hit_count < MAX_SEARCH_HITS) {
            int found = boyer_moore_horspool_search(
                (const unsigned char *)(search_text + pos),
                search_len - pos,
                (const unsigned char *)query_lower,
                query_len,
                last);

            if (found < 0) break;

            int match_pos = pos + found;

            if (whole_word) {
                int before_ok = (match_pos == 0) ||
                    !isalnum((unsigned char)search_text[match_pos - 1]);
                int after_ok = (match_pos + query_len >= search_len) ||
                    !isalnum((unsigned char)search_text[match_pos + query_len]);

                if (!before_ok || !after_ok) {
                    pos = match_pos + 1;
                    continue;
                }
            }

            pdf_search_result_t *result = &out_results->results[hit_count];
            result->page = entry->page;
            result->x = match_pos;
            result->y = 0;
            result->width = query_len;
            result->height = 1;

            size_t ctx_start = (size_t)(match_pos > 20 ? match_pos - 20 : 0);
            size_t ctx_len = (size_t)(query_len + 40);
            if (ctx_start + ctx_len > (size_t)search_len) {
                ctx_len = (size_t)search_len - ctx_start;
            }

            char *ctx_buf = (char *)malloc(ctx_len + 1);
            if (ctx_buf) {
                memcpy(ctx_buf, search_text + ctx_start, ctx_len);
                ctx_buf[ctx_len] = '\0';
                result->text = ctx_buf;
            } else {
                result->text = duplicate_string(query);
            }

            hit_count++;
            pos = match_pos + 1;
        }

        free(entry_lower);
    }

    out_results->count = hit_count;
    free(query_lower);

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL get_suggestions(
    void *handle,
    const char *prefix,
    int32_t max_suggestions,
    pdf_suggestions_t *out_suggestions)
{
    if (!handle || !prefix || !out_suggestions) {
        return PDF_ERR_INVALID_ARG;
    }

    text_index_t *index = (text_index_t *)handle;
    out_suggestions->items = NULL;
    out_suggestions->count = 0;

    if (max_suggestions <= 0 || max_suggestions > MAX_SUGGESTIONS) {
        max_suggestions = MAX_SUGGESTIONS;
    }

    char *prefix_lower = to_lowercase(prefix);
    if (!prefix_lower) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    int prefix_len = (int)strlen(prefix_lower);

    out_suggestions->items = (pdf_suggestion_t *)calloc((size_t)max_suggestions,
                                                         sizeof(pdf_suggestion_t));
    if (!out_suggestions->items) {
        free(prefix_lower);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    int32_t found = 0;
    int32_t *seen_counts = (int32_t *)calloc((size_t)max_suggestions, sizeof(int32_t));

    for (int32_t i = 0; i < index->count && found < max_suggestions; i++) {
        indexed_text_t *entry = &index->entries[i];
        if (!entry->text) continue;

        char *word = entry->text;
        int word_len = entry->length;

        const char *scan = word;
        while (*scan) {
            while (*scan && !isalnum((unsigned char)*scan)) scan++;
            if (!*scan) break;

            const char *word_start = scan;
            while (*scan && isalnum((unsigned char)*scan)) scan++;
            int wlen = (int)(scan - word_start);

            if (wlen >= prefix_len) {
                char *wlower = (char *)malloc((size_t)(wlen + 1));
                if (wlower) {
                    for (int j = 0; j < wlen; j++) {
                        wlower[j] = (char)tolower((unsigned char)word_start[j]);
                    }
                    wlower[wlen] = '\0';

                    if (strncmp(wlower, prefix_lower, prefix_len) == 0) {
                        int32_t dup_idx = -1;
                        for (int32_t k = 0; k < found; k++) {
                            if (out_suggestions->items[k].text &&
                                strcmp(out_suggestions->items[k].text, wlower) == 0) {
                                dup_idx = k;
                                break;
                            }
                        }

                        if (dup_idx >= 0) {
                            seen_counts[dup_idx]++;
                        } else if (found < max_suggestions) {
                            out_suggestions->items[found].text = wlower;
                            out_suggestions->items[found].relevance = 1;
                            seen_counts[found] = 1;
                            found++;
                            wlower = NULL;
                        }
                    }
                    free(wlower);
                }
            }
        }
    }

    for (int32_t i = 0; i < found; i++) {
        out_suggestions->items[i].relevance = seen_counts[i];
    }

    for (int32_t i = 0; i < found - 1; i++) {
        for (int32_t j = i + 1; j < found; j++) {
            if (out_suggestions->items[j].relevance > out_suggestions->items[i].relevance) {
                pdf_suggestion_t tmp = out_suggestions->items[i];
                out_suggestions->items[i] = out_suggestions->items[j];
                out_suggestions->items[j] = tmp;
                int32_t tc = seen_counts[i];
                seen_counts[i] = seen_counts[j];
                seen_counts[j] = tc;
            }
        }
    }

    out_suggestions->count = found;

    free(seen_counts);
    free(prefix_lower);

    return PDF_OK;
}
