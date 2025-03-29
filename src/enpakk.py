import argparse
import hashlib
import os
import random
import pyopencl as cl
import numpy as np
from multiprocessing import Pool, cpu_count

BLOCK_SIZE = 64
BATCH_SIZE = 1024 * 256
MD5_HASH_SIZE = 16

def compress_file(input_path, output_path):
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        while block := fin.read(BLOCK_SIZE):
            md5 = hashlib.md5(block).digest()
            fout.write(md5)

def try_match_block(target_md5: bytes, _):
    candidate = os.urandom(BLOCK_SIZE)
    if hashlib.md5(candidate).digest() == target_md5:
        return candidate
    return None

md5_kernel_code = """
__constant uint r[] = {
    7,12,17,22, 7,12,17,22, 7,12,17,22, 7,12,17,22,
    5,9,14,20, 5,9,14,20, 5,9,14,20, 5,9,14,20,
    4,11,16,23, 4,11,16,23, 4,11,16,23, 4,11,16,23,
    6,10,15,21, 6,10,15,21, 6,10,15,21, 6,10,15,21
};

__constant uint k[] = {
    0xd76aa478,0xe8c7b756,0x242070db,0xc1bdceee,
    0xf57c0faf,0x4787c62a,0xa8304613,0xfd469501,
    0x698098d8,0x8b44f7af,0xffff5bb1,0x895cd7be,
    0x6b901122,0xfd987193,0xa679438e,0x49b40821,
    0xf61e2562,0xc040b340,0x265e5a51,0xe9b6c7aa,
    0xd62f105d,0x02441453,0xd8a1e681,0xe7d3fbc8,
    0x21e1cde6,0xc33707d6,0xf4d50d87,0x455a14ed,
    0xa9e3e905,0xfcefa3f8,0x676f02d9,0x8d2a4c8a,
    0xfffa3942,0x8771f681,0x6d9d6122,0xfde5380c,
    0xa4beea44,0x4bdecfa9,0xf6bb4b60,0xbebfbc70,
    0x289b7ec6,0xeaa127fa,0xd4ef3085,0x04881d05,
    0xd9d4d039,0xe6db99e5,0x1fa27cf8,0xc4ac5665,
    0xf4292244,0x432aff97,0xab9423a7,0xfc93a039,
    0x655b59c3,0x8f0ccc92,0xffeff47d,0x85845dd1,
    0x6fa87e4f,0xfe2ce6e0,0xa3014314,0x4e0811a1,
    0xf7537e82,0xbd3af235,0x2ad7d2bb,0xeb86d391
};

uint leftrotate(uint x, uint c) {
    return (x << c) | (x >> (32 - c));
}

__kernel void md5_hash(__global const uchar *data, __global uchar *hashes, uint block_size) {
    int gid = get_global_id(0);
    __global const uchar *block = data + gid * block_size;
    uint a0 = 0x67452301;
    uint b0 = 0xefcdab89;
    uint c0 = 0x98badcfe;
    uint d0 = 0x10325476;

    uint w[16];
    for (int i = 0; i < 16; i++) {
        w[i] = (uint)block[i*4] | ((uint)block[i*4+1] << 8) |
               ((uint)block[i*4+2] << 16) | ((uint)block[i*4+3] << 24);
    }

    uint a = a0, b = b0, c = c0, d = d0;

    for (int i = 0; i < 64; i++) {
        uint f, g;
        if (i < 16) {
            f = (b & c) | ((~b) & d); g = i;
        } else if (i < 32) {
            f = (d & b) | ((~d) & c); g = (5*i + 1) % 16;
        } else if (i < 48) {
            f = b ^ c ^ d; g = (3*i + 5) % 16;
        } else {
            f = c ^ (b | (~d)); g = (7*i) % 16;
        }

        uint temp = d;
        d = c;
        c = b;
        b = b + leftrotate((a + f + k[i] + w[g]), r[i]);
        a = temp;
    }

    a0 += a; b0 += b; c0 += c; d0 += d;

    __global uchar *hash = hashes + gid * 16;
    hash[ 0] = a0 & 0xff;  hash[ 1] = (a0 >> 8) & 0xff;
    hash[ 2] = (a0 >> 16) & 0xff; hash[ 3] = (a0 >> 24) & 0xff;
    hash[ 4] = b0 & 0xff;  hash[ 5] = (b0 >> 8) & 0xff;
    hash[ 6] = (b0 >> 16) & 0xff; hash[ 7] = (b0 >> 24) & 0xff;
    hash[ 8] = c0 & 0xff;  hash[ 9] = (c0 >> 8) & 0xff;
    hash[10] = (c0 >> 16) & 0xff; hash[11] = (c0 >> 24) & 0xff;
    hash[12] = d0 & 0xff;  hash[13] = (d0 >> 8) & 0xff;
    hash[14] = (d0 >> 16) & 0xff; hash[15] = (d0 >> 24) & 0xff;
}
"""

def decompress_block_gpu(target_md5: bytes, max_attempts: int):
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)
    prg = cl.Program(ctx, md5_kernel_code).build()

    attempts = 0
    while attempts < max_attempts:
        random_blocks = np.random.randint(0, 256, size=BLOCK_SIZE * BATCH_SIZE, dtype=np.uint8)
        mf = cl.mem_flags
        data_buf = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=random_blocks)
        hashes_buf = cl.Buffer(ctx, mf.WRITE_ONLY, size=BATCH_SIZE * MD5_HASH_SIZE)

        prg.md5_hash(queue, (BATCH_SIZE,), None, data_buf, hashes_buf, np.uint32(BLOCK_SIZE))
        hash_results = np.empty(BATCH_SIZE * MD5_HASH_SIZE, dtype=np.uint8)
        cl.enqueue_copy(queue, hash_results, hashes_buf).wait()

        for i in range(BATCH_SIZE):
            hash_candidate = hash_results[i * 16:(i + 1) * 16]
            if bytes(hash_candidate) == target_md5:
                print(f"[GPU] ✓ Found match after {attempts + i} attempts")
                return random_blocks[i * BLOCK_SIZE:(i + 1) * BLOCK_SIZE].tobytes()

        attempts += BATCH_SIZE
        print(f"[GPU] Tried {attempts} blocks...")
        last_hash = hash_results[-16:]
        print(f"Searching for: {target_md5.hex()}")
        print(f"[GPU] Last hash in batch: {bytes(last_hash).hex()}")        

    raise ValueError("Match not found using GPU brute-force.")

# def decompress_block_parallel(md5: bytes, max_attempts: int, workers: int = cpu_count()):
#     print(f"    🧠 Brute-forcing with {workers} workers...")
#     with Pool(processes=workers) as pool:
#         for attempt_start in range(0, max_attempts, workers):
#             tasks = [md5] * workers
#             results = pool.starmap(try_match_block, zip(tasks, range(workers)))
#             for result in results:
#                 if result is not None:
#                     return result
#     raise ValueError("Decompression failed: no match found.")

def decompress_file(input_path, output_path, max_attempts=10**8):
    from multiprocessing import cpu_count
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        block_index = 0
        while md5 := fin.read(16):
            print(f"[+] Decompressing block {block_index}...")
            block = decompress_block_gpu(md5, max_attempts)
            fout.write(block)
            print(f"    ✓ Block {block_index} recovered")
            block_index += 1

def main():
    parser = argparse.ArgumentParser(description="Enpakk — Enthropy Pack Kompressor")
    subparsers = parser.add_subparsers(dest="command")

    compress_parser = subparsers.add_parser("compress", help="Compress into MD5-only archive")
    compress_parser.add_argument("input", help="Input file")
    compress_parser.add_argument("output", help="Output .enpakk archive")

    decompress_parser = subparsers.add_parser("decompress", help="Decompress by brute-force guessing")
    decompress_parser.add_argument("input", help="Input .enpakk archive")
    decompress_parser.add_argument("output", help="Output restored file")
    decompress_parser.add_argument("--max-attempts", type=int, default=10**8,
                                   help="Maximum attempts per block (default: 100 million)")

    args = parser.parse_args()

    if args.command == "compress":
        compress_file(args.input, args.output)
    elif args.command == "decompress":
        decompress_file(args.input, args.output, args.max_attempts)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
