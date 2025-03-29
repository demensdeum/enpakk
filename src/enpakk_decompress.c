#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <zlib.h> // for crc32

#define BLOCK_SIZE 2
#define HASH_SIZE 1
#define CRC32_SIZE 4
#define MAX_CANDIDATES 300

// CRC-8 (poly 0x07)
uint8_t crc8(const uint8_t *data, size_t len) {
    uint8_t crc = 0x00;
    for (size_t i = 0; i < len; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 0x80) {
                crc = ((crc << 1) ^ 0x07) & 0xFF;
            } else {
                crc = (crc << 1) & 0xFF;
            }
        }
    }
    return crc;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <input.enpakk> <output> [--verbose]\n", argv[0]);
        return 1;
    }

    int verbose = 0;
    if (argc >= 4 && strcmp(argv[3], "--verbose") == 0) {
        verbose = 1;
    }

    FILE *fin = fopen(argv[1], "rb");
    if (!fin) {
        perror("fopen input");
        return 1;
    }

    FILE *fout = fopen(argv[2], "wb");
    if (!fout) {
        perror("fopen output");
        fclose(fin);
        return 1;
    }

    // Read expected CRC32
    uint8_t crc_buf[CRC32_SIZE];
    if (fread(crc_buf, 1, CRC32_SIZE, fin) != CRC32_SIZE) {
        fprintf(stderr, "Failed to read CRC32 from file\n");
        return 1;
    }
    uint32_t expected_crc = crc_buf[0] | (crc_buf[1] << 8) | (crc_buf[2] << 16) | (crc_buf[3] << 24);
    if (verbose)
        printf("[INFO] Expected CRC32: 0x%08X\n", expected_crc);

    // Load compressed hash data
    fseek(fin, 0, SEEK_END);
    long file_size = ftell(fin);
    fseek(fin, CRC32_SIZE, SEEK_SET);
    size_t hash_data_len = file_size - CRC32_SIZE;
    uint8_t *hash_data = malloc(hash_data_len);
    if (fread(hash_data, 1, hash_data_len, fin) != hash_data_len) {
        fprintf(stderr, "Failed to read hash data\n");
        return 1;
    }
    fclose(fin);

    srand((unsigned)time(NULL));

    // Precompute all possible blocks by CRC8
    if (verbose)
        printf("[INFO] Precomputing CRC8 candidates...\n");

    uint8_t *candidates[256][MAX_CANDIDATES];
    size_t candidate_counts[256] = {0};

    for (int b1 = 0; b1 < 256; b1++) {
        for (int b2 = 0; b2 < 256; b2++) {
            uint8_t block[2] = { (uint8_t)b1, (uint8_t)b2 };
            uint8_t hash = crc8(block, 2);
            if (candidate_counts[hash] < MAX_CANDIDATES) {
                uint8_t *store = malloc(2);
                memcpy(store, block, 2);
                candidates[hash][candidate_counts[hash]++] = store;
            }
        }
    }

    // Brute force until CRC32 matches
    uint8_t *output_buffer = malloc(hash_data_len * BLOCK_SIZE);
    int attempt = 0;
    while (1) {
        size_t offset = 0;
        for (size_t i = 0; i < hash_data_len; i++) {
            uint8_t hash = hash_data[i];
            size_t count = candidate_counts[hash];
            uint8_t *chosen = candidates[hash][rand() % count];
            output_buffer[offset++] = chosen[0];
            output_buffer[offset++] = chosen[1];
        }

        uint32_t actual_crc = crc32(0L, Z_NULL, 0);
        actual_crc = crc32(actual_crc, output_buffer, offset);

        if (verbose)
            printf("[TRY %d] Actual CRC32: 0x%08X\n", attempt, actual_crc);

        if (actual_crc == expected_crc) {
            if (verbose)
                printf("[✓] CRC32 matched! Decompression complete.\n");
            fwrite(output_buffer, 1, offset, fout);
            break;
        }
        attempt++;
    }

    // Cleanup
    for (int h = 0; h < 256; h++) {
        for (size_t j = 0; j < candidate_counts[h]; j++) {
            free(candidates[h][j]);
        }
    }
    free(hash_data);
    free(output_buffer);
    fclose(fout);

    return 0;
}
