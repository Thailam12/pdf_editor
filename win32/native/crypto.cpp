#include "common.h"

#include <openssl/evp.h>
#include <openssl/aes.h>
#include <openssl/sha.h>
#include <openssl/hmac.h>
#include <openssl/rand.h>
#include <openssl/err.h>
#include <openssl/pem.h>
#include <openssl/x509.h>
#include <openssl/bio.h>

#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define AES_BLOCK_SIZE 16
#define AES256_KEY_SIZE 32
#define AES256_IV_SIZE 16
#define SHA256_DIGEST_SIZE 32
#define MAX_CRYPTO_BUFFER (64 * 1024 * 1024)

static pdf_error_t handle_openssl_error(void) {
    unsigned long err = ERR_get_error();
    if (err == 0) {
        return PDF_ERR_INTERNAL;
    }
    ERR_clear_error();
    return PDF_ERR_ENCRYPTION_FAILED;
}

PDF_EXPORT pdf_error_t PDF_CALL encrypt_aes256(
    const uint8_t *plaintext,
    int32_t plaintext_len,
    const uint8_t *key,
    int32_t key_len,
    uint8_t *ciphertext,
    int32_t *ciphertext_len,
    uint8_t *iv_out)
{
    if (!plaintext || !key || !ciphertext || !ciphertext_len || !iv_out) {
        return PDF_ERR_INVALID_ARG;
    }

    if (key_len != AES256_KEY_SIZE) {
        return PDF_ERR_INVALID_ARG;
    }

    if (plaintext_len < 0 || plaintext_len > MAX_CRYPTO_BUFFER) {
        return PDF_ERR_INVALID_ARG;
    }

    uint8_t iv[AES256_IV_SIZE];
    if (RAND_bytes(iv, AES256_IV_SIZE) != 1) {
        return handle_openssl_error();
    }

    memcpy(iv_out, iv, AES256_IV_SIZE);

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pdf_error_t result = PDF_OK;

    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv) != 1) {
        result = handle_openssl_error();
        EVP_CIPHER_CTX_free(ctx);
        return result;
    }

    EVP_CIPHER_CTX_set_padding(ctx, 1);

    int len = 0;
    int total_len = 0;

    if (EVP_EncryptUpdate(ctx, ciphertext, &len, plaintext, plaintext_len) != 1) {
        result = handle_openssl_error();
        EVP_CIPHER_CTX_free(ctx);
        return result;
    }
    total_len = len;

    if (EVP_EncryptFinal_ex(ctx, ciphertext + len, &len) != 1) {
        result = handle_openssl_error();
        EVP_CIPHER_CTX_free(ctx);
        return result;
    }
    total_len += len;

    *ciphertext_len = total_len;

    EVP_CIPHER_CTX_free(ctx);
    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL decrypt_aes256(
    const uint8_t *ciphertext,
    int32_t ciphertext_len,
    const uint8_t *key,
    int32_t key_len,
    const uint8_t *iv,
    int32_t iv_len,
    uint8_t *plaintext,
    int32_t *plaintext_len)
{
    if (!ciphertext || !key || !iv || !plaintext || !plaintext_len) {
        return PDF_ERR_INVALID_ARG;
    }

    if (key_len != AES256_KEY_SIZE) {
        return PDF_ERR_INVALID_ARG;
    }

    if (iv_len != AES256_IV_SIZE) {
        return PDF_ERR_INVALID_ARG;
    }

    if (ciphertext_len <= 0 || ciphertext_len > MAX_CRYPTO_BUFFER) {
        return PDF_ERR_INVALID_ARG;
    }

    if (ciphertext_len % AES_BLOCK_SIZE != 0) {
        return PDF_ERR_INVALID_ARG;
    }

    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pdf_error_t result = PDF_OK;

    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv) != 1) {
        result = handle_openssl_error();
        EVP_CIPHER_CTX_free(ctx);
        return result;
    }

    EVP_CIPHER_CTX_set_padding(ctx, 1);

    int len = 0;
    int total_len = 0;

    if (EVP_DecryptUpdate(ctx, plaintext, &len, ciphertext, ciphertext_len) != 1) {
        result = PDF_ERR_DECRYPTION_FAILED;
        EVP_CIPHER_CTX_free(ctx);
        return result;
    }
    total_len = len;

    if (EVP_DecryptFinal_ex(ctx, plaintext + len, &len) != 1) {
        result = PDF_ERR_DECRYPTION_FAILED;
        EVP_CIPHER_CTX_free(ctx);
        return result;
    }
    total_len += len;

    *plaintext_len = total_len;

    EVP_CIPHER_CTX_free(ctx);
    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL compute_hash(
    const uint8_t *data,
    int32_t data_len,
    int32_t algorithm,
    uint8_t *hash_out,
    int32_t *hash_len)
{
    if (!data || !hash_out || !hash_len) {
        return PDF_ERR_INVALID_ARG;
    }

    if (data_len < 0) {
        return PDF_ERR_INVALID_ARG;
    }

    const EVP_MD *md = NULL;

    switch (algorithm) {
        case 0: md = EVP_sha256(); break;
        case 1: md = EVP_sha512(); break;
        case 2: md = EVP_sha1(); break;
        case 3: md = EVP_md5(); break;
        default: md = EVP_sha256(); break;
    }

    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pdf_error_t result = PDF_OK;

    if (EVP_DigestInit_ex(ctx, md, NULL) != 1) {
        result = handle_openssl_error();
        EVP_MD_CTX_free(ctx);
        return result;
    }

    if (data_len > 0) {
        if (EVP_DigestUpdate(ctx, data, (size_t)data_len) != 1) {
            result = handle_openssl_error();
            EVP_MD_CTX_free(ctx);
            return result;
        }
    }

    unsigned int md_len = 0;
    if (EVP_DigestFinal_ex(ctx, hash_out, &md_len) != 1) {
        result = handle_openssl_error();
        EVP_MD_CTX_free(ctx);
        return result;
    }

    *hash_len = (int32_t)md_len;

    EVP_MD_CTX_free(ctx);
    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL compute_hash_file(
    const char *file_path,
    int32_t algorithm,
    uint8_t *hash_out,
    int32_t *hash_len)
{
    if (!file_path || !hash_out || !hash_len) {
        return PDF_ERR_INVALID_ARG;
    }

    FILE *f = fopen(file_path, "rb");
    if (!f) {
        return PDF_ERR_FILE_NOT_FOUND;
    }

    const EVP_MD *md = NULL;
    switch (algorithm) {
        case 0: md = EVP_sha256(); break;
        case 1: md = EVP_sha512(); break;
        case 2: md = EVP_sha1(); break;
        case 3: md = EVP_md5(); break;
        default: md = EVP_sha256(); break;
    }

    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    if (!ctx) {
        fclose(f);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pdf_error_t result = PDF_OK;

    if (EVP_DigestInit_ex(ctx, md, NULL) != 1) {
        result = handle_openssl_error();
        EVP_MD_CTX_free(ctx);
        fclose(f);
        return result;
    }

    uint8_t buffer[65536];
    size_t bytes_read;

    while ((bytes_read = fread(buffer, 1, sizeof(buffer), f)) > 0) {
        if (EVP_DigestUpdate(ctx, buffer, bytes_read) != 1) {
            result = handle_openssl_error();
            EVP_MD_CTX_free(ctx);
            fclose(f);
            return result;
        }
    }

    fclose(f);

    unsigned int md_len = 0;
    if (EVP_DigestFinal_ex(ctx, hash_out, &md_len) != 1) {
        result = handle_openssl_error();
        EVP_MD_CTX_free(ctx);
        return result;
    }

    *hash_len = (int32_t)md_len;

    EVP_MD_CTX_free(ctx);
    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL verify_signature(
    const uint8_t *data,
    int32_t data_len,
    const uint8_t *signature,
    int32_t signature_len,
    const uint8_t *public_key,
    int32_t public_key_len,
    int32_t algorithm,
    int32_t *out_valid)
{
    if (!data || !signature || !public_key || !out_valid) {
        return PDF_ERR_INVALID_ARG;
    }

    *out_valid = 0;

    if (data_len < 0 || signature_len <= 0 || public_key_len <= 0) {
        return PDF_ERR_INVALID_ARG;
    }

    const EVP_MD *md = NULL;
    switch (algorithm) {
        case 0: md = EVP_sha256(); break;
        case 1: md = EVP_sha512(); break;
        case 2: md = EVP_sha1(); break;
        default: md = EVP_sha256(); break;
    }

    EVP_MD_CTX *mdctx = EVP_MD_CTX_new();
    if (!mdctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    EVP_PKEY *pkey = NULL;
    BIO *bio = BIO_new_mem_buf(public_key, public_key_len);
    if (!bio) {
        EVP_MD_CTX_free(mdctx);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pkey = PEM_read_bio_PUBKEY(bio, NULL, NULL, NULL);
    BIO_free(bio);

    if (!pkey) {
        pkey = d2i_PUBKEY(NULL, (const unsigned char **)&public_key, public_key_len);
        if (!pkey) {
            EVP_MD_CTX_free(mdctx);
            return PDF_ERR_INVALID_ARG;
        }
    }

    pdf_error_t result = PDF_OK;
    int verify_result = EVP_DigestVerifyInit(mdctx, NULL, md, NULL, pkey);

    if (verify_result != 1) {
        result = handle_openssl_error();
        EVP_PKEY_free(pkey);
        EVP_MD_CTX_free(mdctx);
        return result;
    }

    if (EVP_DigestVerifyUpdate(mdctx, data, (size_t)data_len) != 1) {
        result = handle_openssl_error();
        EVP_PKEY_free(pkey);
        EVP_MD_CTX_free(mdctx);
        return result;
    }

    int verify_final = EVP_DigestVerifyFinal(mdctx, signature, (size_t)signature_len);
    *out_valid = (verify_final == 1) ? 1 : 0;

    EVP_PKEY_free(pkey);
    EVP_MD_CTX_free(mdctx);

    return result;
}

PDF_EXPORT pdf_error_t PDF_CALL generate_key_pair(
    int32_t key_bits,
    uint8_t *public_key_out,
    int32_t *public_key_len,
    uint8_t *private_key_out,
    int32_t *private_key_len)
{
    if (!public_key_out || !public_key_len || !private_key_out || !private_key_len) {
        return PDF_ERR_INVALID_ARG;
    }

    if (key_bits < 2048) key_bits = 2048;

    EVP_PKEY_CTX *pctx = EVP_PKEY_CTX_new_id(EVP_PKEY_RSA, NULL);
    if (!pctx) {
        return PDF_ERR_OUT_OF_MEMORY;
    }

    pdf_error_t result = PDF_OK;

    if (EVP_PKEY_keygen_init(pctx) <= 0) {
        result = handle_openssl_error();
        EVP_PKEY_CTX_free(pctx);
        return result;
    }

    if (EVP_PKEY_CTX_set_rsa_keygen_bits(pctx, key_bits) <= 0) {
        result = handle_openssl_error();
        EVP_PKEY_CTX_free(pctx);
        return result;
    }

    EVP_PKEY *pkey = NULL;
    if (EVP_PKEY_keygen(pctx, &pkey) <= 0) {
        result = handle_openssl_error();
        EVP_PKEY_CTX_free(pctx);
        return result;
    }

    EVP_PKEY_CTX_free(pctx);

    BIO *pub_bio = BIO_new(BIO_s_mem());
    BIO *priv_bio = BIO_new(BIO_s_mem());

    if (!pub_bio || !priv_bio) {
        EVP_PKEY_free(pkey);
        BIO_free(pub_bio);
        BIO_free(priv_bio);
        return PDF_ERR_OUT_OF_MEMORY;
    }

    PEM_write_bio_PUBKEY(pub_bio, pkey);
    PEM_write_bio_PrivateKey(priv_bio, pkey, NULL, NULL, 0, NULL, NULL);

    char *pub_data = NULL;
    long pub_len = BIO_get_mem_data(pub_bio, &pub_data);
    char *priv_data = NULL;
    long priv_len = BIO_get_mem_data(priv_bio, &priv_data);

    if (pub_len > *public_key_len || priv_len > *private_key_len) {
        *public_key_len = (int32_t)pub_len;
        *private_key_len = (int32_t)priv_len;
        EVP_PKEY_free(pkey);
        BIO_free(pub_bio);
        BIO_free(priv_bio);
        return PDF_ERR_BUFFER_TOO_SMALL;
    }

    memcpy(public_key_out, pub_data, (size_t)pub_len);
    *public_key_len = (int32_t)pub_len;
    memcpy(private_key_out, priv_data, (size_t)priv_len);
    *private_key_len = (int32_t)priv_len;

    EVP_PKEY_free(pkey);
    BIO_free(pub_bio);
    BIO_free(priv_bio);

    return result;
}
