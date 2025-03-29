# enpakk.py

import argparse
import hashlib
import random
import struct
import os

BLOCK_SIZE = 4096

def compress_block(block: bytes, seed: int):
    rng = random.Random(seed)
    rand_bytes = bytes([rng.randint(0, 255) for _ in range(len(block))])
    encoded = bytes([b ^ r for b, r in zip(block, rand_bytes)])
    md5 = hashlib.md5(block).digest()
    return struct.pack("<I", seed) + md5 + encoded  # 4-byte seed + 16-byte md5 + data

def decompress_block(data: bytes):
    seed = struct.unpack("<I", data[:4])[0]
    md5 = data[4:20]
    encoded = data[20:]
    rng = random.Random(seed)
    rand_bytes = bytes([rng.randint(0, 255) for _ in range(len(encoded))])
    decoded = bytes([b ^ r for b, r in zip(encoded, rand_bytes)])
    if hashlib.md5(decoded).digest() != md5:
        raise ValueError("Block MD5 mismatch!")
    return decoded

def compress_file(input_path, output_path):
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        while block := fin.read(BLOCK_SIZE):
            seed = random.randint(0, 0xFFFFFFFF)
            fout.write(compress_block(block, seed))

def decompress_file(input_path, output_path):
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        while True:
            seed_bytes = fin.read(4)
            if not seed_bytes:
                break
            md5 = fin.read(16)
            encoded_block = fin.read(BLOCK_SIZE)
            if len(encoded_block) == 0:
                break
            block_data = seed_bytes + md5 + encoded_block
            decoded = decompress_block(block_data)
            fout.write(decoded)

def main():
    parser = argparse.ArgumentParser(description="Random Block Compressor (randzip)")
    subparsers = parser.add_subparsers(dest="command")

    compress_parser = subparsers.add_parser("compress")
    compress_parser.add_argument("input", help="Input file to compress")
    compress_parser.add_argument("output", help="Output compressed file")

    decompress_parser = subparsers.add_parser("decompress")
    decompress_parser.add_argument("input", help="Compressed input file")
    decompress_parser.add_argument("output", help="Decompressed output file")

    args = parser.parse_args()

    if args.command == "compress":
        compress_file(args.input, args.output)
    elif args.command == "decompress":
        decompress_file(args.input, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
