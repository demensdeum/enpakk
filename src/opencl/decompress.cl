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

__kernel void brute_crc32(
    __global const uchar *flat_blocks,
    __global const int *block_indices,
    const int blocks_per_output,
    const int total_outputs,
    const uint expected_crc,
    __global uchar *output_data,
    __global int *found_flag,
    __global uchar *found_output
) {
    int gid = get_global_id(0);
    if (gid >= total_outputs || *found_flag != 0)
        return;

    __global uchar *output_ptr = output_data + gid * (blocks_per_output * 2);
    for (int i = 0; i < blocks_per_output; i++) {
        int offset = block_indices[i];
        int idx = (gid + i) % 300;
        __global const uchar *block = flat_blocks + (offset + idx) * 2;
        output_ptr[i * 2 + 0] = block[0];
        output_ptr[i * 2 + 1] = block[1];
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
