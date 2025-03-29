#include <metal_stdlib>
using namespace metal;

#define BLOCK_SIZE 2
#define MAX_CANDIDATES 300

uint32_t crc32_update(uint32_t crc, uint8_t data) {
    crc ^= data;
    for (int k = 0; k < 8; k++) {
        crc = (crc & 1) ? (crc >> 1) ^ 0xEDB88320 : crc >> 1;
    }
    return crc;
}

uint32_t compute_crc32(thread const uint8_t* data, uint len) {
    uint32_t crc = 0xFFFFFFFF;
    for (uint i = 0; i < len; i++) {
        crc = crc32_update(crc, data[i]);
    }
    return ~crc;
}

kernel void bruteForceDecompress(
    device const uint8_t* hash_data [[ buffer(0) ]],
    device const uint8_t* candidates [[ buffer(1) ]],
    device const uint32_t* candidate_counts [[ buffer(2) ]],
    constant uint32_t& hash_len [[ buffer(3) ]],
    constant uint32_t& expected_crc [[ buffer(4) ]],
    device uint8_t* result_buffer [[ buffer(5) ]],
    device atomic_uint* found_flag [[ buffer(6) ]],
    uint threadID [[ thread_position_in_grid ]]
) {
    if (atomic_load_explicit(found_flag, memory_order_relaxed) != 0) return;

    uint8_t output[2048];
    uint offset = 0;

    for (uint i = 0; i < hash_len; i++) {
        uint8_t hash = hash_data[i];
        uint count = candidate_counts[hash];
        if (count == 0) return;

        uint idx = (threadID + i * 13) % count;
        uint base = ((uint)hash * MAX_CANDIDATES + idx) * 2;
        output[offset++] = candidates[base];
        output[offset++] = candidates[base + 1];
    }

    uint32_t crc = compute_crc32(output, offset);

    if (crc == expected_crc) {
        for (uint i = 0; i < offset; i++) {
            result_buffer[i] = output[i];
        }
        atomic_store_explicit(found_flag, 1, memory_order_relaxed);
    }
}
