#pragma OPENCL EXTENSION cl_khr_byte_addressable_store : enable

#define CRC32_POLY 0xEDB88320

uint crc32(uint crc, __global const uchar *data, uint len) {
    crc = ~crc;
    for (uint i = 0; i < len; i++) {
        uint byte = data[i];
        crc ^= byte;
        for (uint j = 0; j < 8; j++) {
            uint mask = -(int)(crc & 1);
            crc = (crc >> 1) ^ (CRC32_POLY & mask);
        }
    }
    return ~crc;
}

// A very basic Xorshift32 PRNG
uint xorshift32(uint x) {
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    return x;
}

__kernel void brute_crc32(
    __global const uchar *flat_blocks,         // arg0
    __global const int *block_indices,         // arg1
    const int blocks_per_output,               // arg2
    const int total_outputs,                   // arg3
    const uint expected_crc,                   // arg4
    __global uchar *output_data,               // arg5
    __global int *found_flag,                  // arg6
    __global uchar *found_output,              // arg7
    __global const int *seed_ptr               // arg8
) {
    int gid = get_global_id(0);
    if (gid >= total_outputs || *found_flag != 0)
        return;

    // Initialize random state from seed and gid
    int seed = seed_ptr[0] ^ gid;
    seed = xorshift32(seed);

    __global uchar *output_ptr = output_data + gid * (blocks_per_output * 2);

    for (int i = 0; i < blocks_per_output; i++) {
        int offset = block_indices[i];
        int idx = seed % 300; // max candidate index
        __global const uchar *block = flat_blocks + (offset + idx) * 2;

        output_ptr[i * 2 + 0] = block[0];
        output_ptr[i * 2 + 1] = block[1];

        seed = xorshift32(seed + i);
    }

    uint crc = crc32(0, output_ptr, blocks_per_output * 2);

    if (crc == expected_crc) {
        if (atomic_cmpxchg(found_flag, 0, 1) == 0) {
            for (int i = 0; i < blocks_per_output * 2; i++) {
                found_output[i] = output_ptr[i];
            }
        }
    }
}
