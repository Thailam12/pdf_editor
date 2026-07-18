#include "common.h"

#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <float.h>

#define PI 3.14159265358979323846f
#define HISTOGRAM_BINS 256

static inline uint8_t clamp_u8(int val) {
    if (val < 0) return 0;
    if (val > 255) return 255;
    return (uint8_t)val;
}

static inline int abs_int(int val) {
    return val < 0 ? -val : val;
}

static void compute_histogram(const uint8_t *data, int32_t width, int32_t height,
                               int32_t stride, int32_t *histogram) {
    memset(histogram, 0, HISTOGRAM_BINS * sizeof(int32_t));
    for (int32_t y = 0; y < height; y++) {
        for (int32_t x = 0; x < width; x++) {
            histogram[data[y * stride + x]]++;
        }
    }
}

static int32_t otsu_threshold(const int32_t *histogram, int32_t total_pixels) {
    float sum = 0.0f;
    for (int32_t i = 0; i < HISTOGRAM_BINS; i++) {
        sum += (float)(i * histogram[i]);
    }

    float sumB = 0.0f;
    int32_t wB = 0;
    float max_variance = 0.0f;
    int32_t best_threshold = 128;

    for (int32_t t = 0; t < HISTOGRAM_BINS; t++) {
        wB += histogram[t];
        if (wB == 0) continue;

        int32_t wF = total_pixels - wB;
        if (wF == 0) break;

        sumB += (float)(t * histogram[t]);

        float meanB = sumB / (float)wB;
        float meanF = (sum - sumB) / (float)wF;
        float diff = meanB - meanF;
        float variance = (float)wB * (float)wF * diff * diff;

        if (variance > max_variance) {
            max_variance = variance;
            best_threshold = t;
        }
    }

    return best_threshold;
}

PDF_EXPORT pdf_error_t PDF_CALL binarize(
    const uint8_t *input,
    int32_t width,
    int32_t height,
    int32_t stride,
    int32_t method,
    uint8_t *output)
{
    if (!input || !output || width <= 0 || height <= 0) {
        return PDF_ERR_INVALID_ARG;
    }

    if (method == 0) {
        int32_t histogram[HISTOGRAM_BINS];
        compute_histogram(input, width, height, stride, histogram);
        int32_t threshold = otsu_threshold(histogram, width * height);

        for (int32_t y = 0; y < height; y++) {
            for (int32_t x = 0; x < width; x++) {
                output[y * width + x] = (input[y * stride + x] >= threshold) ? 255 : 0;
            }
        }
    } else if (method == 1) {
        int32_t block_size = 31;
        int32_t C = 10;
        int32_t half_block = block_size / 2;

        int32_t *integral = (int32_t *)calloc((size_t)(width + 1) * (height + 1), sizeof(int32_t));
        if (!integral) {
            return PDF_ERR_OUT_OF_MEMORY;
        }

        for (int32_t y = 0; y < height; y++) {
            int32_t row_sum = 0;
            for (int32_t x = 0; x < width; x++) {
                row_sum += input[y * stride + x];
                integral[(y + 1) * (width + 1) + (x + 1)] =
                    row_sum + integral[y * (width + 1) + (x + 1)];
            }
        }

        for (int32_t y = 0; y < height; y++) {
            for (int32_t x = 0; x < width; x++) {
                int32_t x1 = PDF_MAX(0, x - half_block);
                int32_t y1 = PDF_MAX(0, y - half_block);
                int32_t x2 = PDF_MIN(width - 1, x + half_block);
                int32_t y2 = PDF_MIN(height - 1, y + half_block);

                int32_t area = (x2 - x1 + 1) * (y2 - y1 + 1);
                int32_t sum = integral[(y2 + 1) * (width + 1) + (x2 + 1)]
                            - integral[y1 * (width + 1) + (x2 + 1)]
                            - integral[(y2 + 1) * (width + 1) + x1]
                            + integral[y1 * (width + 1) + x1];

                int32_t threshold = (sum / area) - C;
                output[y * width + x] = (input[y * stride + x] > threshold) ? 255 : 0;
            }
        }

        free(integral);
    } else {
        return PDF_ERR_INVALID_ARG;
    }

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL denoise(
    const uint8_t *input,
    int32_t width,
    int32_t height,
    int32_t stride,
    int32_t strength,
    uint8_t *output)
{
    if (!input || !output || width <= 0 || height <= 0) {
        return PDF_ERR_INVALID_ARG;
    }

    if (strength < 1) strength = 1;
    if (strength > 10) strength = 10;

    int kernel_size = strength * 2 + 1;
    int kernel_area = kernel_size * kernel_size;
    int half_kernel = strength;

    int32_t *temp = (int32_t *)malloc((size_t)width * height * sizeof(int32_t));
    if (!temp) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    for (int32_t y = 0; y < height; y++) {
        for (int32_t x = 0; x < width; x++) {
            int sum = 0;
            int count = 0;
            int center = input[y * stride + x];

            for (int ky = -half_kernel; ky <= half_kernel; ky++) {
                for (int kx = -half_kernel; kx <= half_kernel; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                        int val = input[ny * stride + nx];
                        if (abs_int(val - center) < 30) {
                            sum += val;
                            count++;
                        }
                    }
                }
            }

            temp[y * width + x] = (count > 0) ? (sum / count) : center;
        }
    }

    for (int32_t y = 0; y < height; y++) {
        for (int32_t x = 0; x < width; x++) {
            output[y * width + x] = clamp_u8(temp[y * width + x]);
        }
    }

    free(temp);
    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL deskew(
    const uint8_t *input,
    int32_t width,
    int32_t height,
    int32_t stride,
    float *out_angle,
    uint8_t *output)
{
    if (!input || !output || width <= 0 || height <= 0 || !out_angle) {
        return PDF_ERR_INVALID_ARG;
    }

    *out_angle = 0.0f;

    int32_t histogram[HISTOGRAM_BINS];
    compute_histogram(input, width, height, stride, histogram);
    int32_t threshold = otsu_threshold(histogram, width * height);

    int32_t *projection = (int32_t *)calloc((size_t)height, sizeof(int32_t));
    if (!projection) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    for (int32_t y = 0; y < height; y++) {
        int32_t count = 0;
        for (int32_t x = 0; x < width; x++) {
            if (input[y * stride + x] < threshold) {
                count++;
            }
        }
        projection[y] = count;
    }

    float best_angle = 0.0f;
    float min_variance = FLT_MAX;

    for (float angle = -5.0f; angle <= 5.0f; angle += 0.1f) {
        float rad = angle * PI / 180.0f;
        float cos_a = cosf(rad);
        float sin_a = sinf(rad);

        float *rotated = (float *)calloc((size_t)height, sizeof(float));
        float *rotated_count = (float *)calloc((size_t)height, sizeof(float));
        if (!rotated || !rotated_count) {
            free(rotated);
            free(rotated_count);
            continue;
        }

        int32_t sample_step = PDF_MAX(1, width / 50);
        int32_t sample_count = 0;

        for (int32_t y = 0; y < height; y += 2) {
            for (int32_t x = 0; x < width; x += sample_step) {
                if (input[y * stride + x] < threshold) {
                    float ry = (float)y * cos_a - (float)x * sin_a;
                    int32_t ry_i = (int32_t)(ry + 0.5f);
                    if (ry_i >= 0 && ry_i < height) {
                        rotated[ry_i] += 1.0f;
                        rotated_count[ry_i] += 1.0f;
                    }
                }
            }
        }

        float mean = 0.0f;
        float total = 0.0f;
        for (int32_t i = 0; i < height; i++) {
            if (rotated_count[i] > 0) {
                mean += rotated[i];
                total += 1.0f;
            }
        }
        if (total > 0) mean /= total;

        float variance = 0.0f;
        for (int32_t i = 0; i < height; i++) {
            float diff = rotated[i] - mean;
            variance += diff * diff;
        }
        if (total > 0) variance /= total;

        if (variance < min_variance) {
            min_variance = variance;
            best_angle = angle;
        }

        free(rotated);
        free(rotated_count);
    }

    *out_angle = best_angle;

    float rad = best_angle * PI / 180.0f;
    float cos_a = cosf(rad);
    float sin_a = sinf(rad);
    float cx = (float)width / 2.0f;
    float cy = (float)height / 2.0f;

    memset(output, 255, (size_t)width * height);

    for (int32_t y = 0; y < height; y++) {
        for (int32_t x = 0; x < width; x++) {
            float dx = (float)x - cx;
            float dy = (float)y - cy;

            float src_x = dx * cos_a + dy * sin_a + cx;
            float src_y = -dx * sin_a + dy * cos_a + cy;

            int32_t sx = (int32_t)src_x;
            int32_t sy = (int32_t)src_y;

            if (sx >= 0 && sx < width && sy >= 0 && sy < height) {
                output[y * width + x] = input[sy * stride + sx];
            }
        }
    }

    free(projection);
    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL sharpen(
    const uint8_t *input,
    int32_t width,
    int32_t height,
    int32_t stride,
    float amount,
    uint8_t *output)
{
    if (!input || !output || width <= 0 || height <= 0) {
        return PDF_ERR_INVALID_ARG;
    }

    if (amount < 0.0f) amount = 0.0f;
    if (amount > 2.0f) amount = 2.0f;

    static const float sharpen_kernel[3][3] = {
        { 0.0f, -1.0f,  0.0f},
        {-1.0f,  4.0f, -1.0f},
        { 0.0f, -1.0f,  0.0f}
    };

    float kernel[3][3];
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            kernel[i][j] = sharpen_kernel[i][j] * amount;
        }
    }
    kernel[1][1] += 1.0f;

    for (int32_t y = 0; y < height; y++) {
        for (int32_t x = 0; x < width; x++) {
            float sum = 0.0f;

            for (int ky = -1; ky <= 1; ky++) {
                for (int kx = -1; kx <= 1; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < height && nx >= 0 && nx < width) {
                        sum += (float)input[ny * stride + nx] * kernel[ky + 1][kx + 1];
                    } else {
                        sum += (float)input[y * stride + x] * kernel[ky + 1][kx + 1];
                    }
                }
            }

            output[y * width + x] = clamp_u8((int)(sum + 0.5f));
        }
    }

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL enhance_contrast(
    const uint8_t *input,
    int32_t width,
    int32_t height,
    int32_t stride,
    float factor,
    uint8_t *output)
{
    if (!input || !output || width <= 0 || height <= 0) {
        return PDF_ERR_INVALID_ARG;
    }

    if (factor < 0.0f) factor = 0.0f;
    if (factor > 2.0f) factor = 2.0f;

    int32_t histogram[HISTOGRAM_BINS];
    compute_histogram(input, width, height, stride, histogram);

    int32_t total = width * height;
    int32_t cumulative = 0;
    uint8_t lut[HISTOGRAM_BINS];

    int32_t min_val = 0;
    int32_t max_val = 255;

    while (min_val < 255 && histogram[min_val] == 0) min_val++;
    while (max_val > 0 && histogram[max_val] == 0) max_val--;

    if (min_val >= max_val) {
        memcpy(output, input, (size_t)height * stride);
        return PDF_OK;
    }

    int32_t range = max_val - min_val;

    for (int32_t i = 0; i < HISTOGRAM_BINS; i++) {
        cumulative += histogram[i];
        float normalized = (float)(cumulative - histogram[min_val]) /
                          (float)(total - histogram[min_val]);
        lut[i] = clamp_u8((int)(min_val + normalized * range + 0.5f));
    }

    float mid = 128.0f;
    for (int32_t y = 0; y < height; y++) {
        for (int32_t x = 0; x < width; x++) {
            float val = (float)lut[input[y * stride + x]];
            val = mid + (val - mid) * factor;
            output[y * width + x] = clamp_u8((int)(val + 0.5f));
        }
    }

    return PDF_OK;
}

PDF_EXPORT pdf_error_t PDF_CALL ocr_preprocess_full(
    const uint8_t *input,
    int32_t width,
    int32_t height,
    int32_t stride,
    int32_t flags,
    uint8_t *output,
    float *out_angle)
{
    if (!input || !output || width <= 0 || height <= 0) {
        return PDF_ERR_INVALID_ARG;
    }

    uint8_t *temp1 = (uint8_t *)malloc((size_t)width * height);
    uint8_t *temp2 = (uint8_t *)malloc((size_t)width * height);
    if (!temp1 || !temp2) {
        free(temp1);
        free(temp2);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pdf_error_t err = PDF_OK;
    float angle = 0.0f;

    if (flags & 0x01) {
        err = enhance_contrast(input, width, height, stride, 1.5f, temp1);
        if (err != PDF_OK) goto cleanup;
    } else {
        for (int32_t y = 0; y < height; y++) {
            memcpy(temp1 + y * width, input + y * stride, (size_t)width);
        }
    }

    if (flags & 0x02) {
        err = denoise(temp1, width, height, width, 2, temp2);
        if (err != PDF_OK) goto cleanup;
    } else {
        memcpy(temp2, temp1, (size_t)width * height);
    }

    if (flags & 0x04) {
        err = deskew(temp2, width, height, width, &angle, temp1);
        if (err != PDF_OK) goto cleanup;
    } else {
        memcpy(temp1, temp2, (size_t)width * height);
    }

    if (flags & 0x08) {
        err = sharpen(temp1, width, height, width, 1.0f, temp2);
        if (err != PDF_OK) goto cleanup;
    } else {
        memcpy(temp2, temp1, (size_t)width * height);
    }

    if (flags & 0x10) {
        err = binarize(temp2, width, height, width, 0, output);
        if (err != PDF_OK) goto cleanup;
    } else {
        memcpy(output, temp2, (size_t)width * height);
    }

    if (out_angle) {
        *out_angle = angle;
    }

cleanup:
    free(temp1);
    free(temp2);
    return err;
}
