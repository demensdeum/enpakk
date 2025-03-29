# This is the CPU-side code that sets up and runs the CUDA kernel for brute-forcing xxh32.
# The actual CUDA kernel will be inlined in a string.

import argparse
import os
import numpy as np
import pycuda.autoinit
import pycuda.driver as cuda
from pycuda.compiler import SourceModule

BLOCK_SIZE = 4  # 4 bytes = 32 bits
HASH_SIZE = 4   # 32-bit hash
BATCH_SIZE = 1024 * 256

cuda_kernel_code = """
__device__ uint32_t rotl32(uint32_t x, int r) {
    return (x << r) | (x >> (32 - r));
}

__device__ uint32_t xxh32(const uint8_t* input, uint32_t seed) {
    const uint32_t PRIME1 = 2654435761U;
    const uint32_t PRIME2 = 2246822519U;
    const uint32_t PRIME3 = 3266489917U;
    const uint32_t PRIME4 = 668265263U;
    const uint32_t PRIME5 = 374761393U;

    uint32_t h32 = seed + PRIME5 + 4;
    h32 += (*(uint32_t*)input) * PRIME3;
    h32 = rotl32(h32, 17) * PRIME4;
    h32 ^= h32 >> 15;
    h32 *= PRIME2;
    h32 ^= h32 >> 13;
    h32 *= PRIME3;
    h32 ^= h32 >> 16;

    return h32;
}

extern "C"
__global__ void brute_xxh32(uint8_t* output_blocks, uint32_t* output_hashes, uint32_t target_hash, uint32_t* match_idx, int* found) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (*found) return;

    uint32_t val = idx;
    uint8_t block[4];
    block[0] = val & 0xFF;
    block[1] = (val >> 8) & 0xFF;
    block[2] = (val >> 16) & 0xFF;
    block[3] = (val >> 24) & 0xFF;

    uint32_t h = xxh32(block, 0);
    output_hashes[idx] = h;
    *(uint32_t*)(output_blocks + idx * 4) = *(uint32_t*)block;

    if (h == target_hash) {
        *match_idx = idx;
        *found = 1;
    }
}
"""

def decompress_block_cuda(target_hash_bytes):
    mod = SourceModule(cuda_kernel_code)
    kernel = mod.get_function("brute_xxh32")

    target_hash = np.frombuffer(target_hash_bytes, dtype=np.uint32)[0]

    output_blocks = np.zeros((BATCH_SIZE, BLOCK_SIZE), dtype=np.uint8)
    output_hashes = np.zeros(BATCH_SIZE, dtype=np.uint32)
    match_idx = np.zeros(1, dtype=np.uint32)
    found_flag = np.zeros(1, dtype=np.int32)

    d_output_blocks = cuda.mem_alloc(output_blocks.nbytes)
    d_output_hashes = cuda.mem_alloc(output_hashes.nbytes)
    d_match_idx = cuda.mem_alloc(match_idx.nbytes)
    d_found_flag = cuda.mem_alloc(found_flag.nbytes)

    cuda.memcpy_htod(d_match_idx, match_idx)
    cuda.memcpy_htod(d_found_flag, found_flag)

    threads = 256
    blocks = (BATCH_SIZE + threads - 1) // threads

    kernel(d_output_blocks, d_output_hashes, np.uint32(target_hash), d_match_idx, d_found_flag,
           block=(threads,1,1), grid=(blocks,1))

    cuda.memcpy_dtoh(found_flag, d_found_flag)
    cuda.memcpy_dtoh(match_idx, d_match_idx)
    if found_flag[0]:
        cuda.memcpy_dtoh(output_blocks, d_output_blocks)
        return bytes(output_blocks[match_idx[0]])
    else:
        raise ValueError("No match found")

def decompress_file(input_path, output_path):
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        block_index = 0
        while True:
            hash_bytes = fin.read(HASH_SIZE)
            if not hash_bytes:
                break
            print(f"[+] Decompressing block {block_index} - {int.from_bytes(hash_bytes, 'little')}...")
            block = decompress_block_cuda(hash_bytes)
            fout.write(block)
            print(f"    ✓ Block {block_index} recovered")
            block_index += 1

def main():
    parser = argparse.ArgumentParser(description="Enpakk CUDA xxh32 Brute-force Decompressor")
    parser.add_argument("input", help="Input .enpakk archive")
    parser.add_argument("output", help="Output file")
    args = parser.parse_args()
    decompress_file(args.input, args.output)

if __name__ == "__main__":
    main()
