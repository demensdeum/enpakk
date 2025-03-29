import argparse
import os
import itertools
import random
import zlib

BLOCK_SIZE = 2  # Original data block is 2 bytes
HASH_SIZE = 1   # 1-byte CRC-8 hash
CRC32_SIZE = 4  # 4-byte CRC32 stored at start

# CRC-8 implementation (poly 0x07)
def crc8(data: bytes, poly: int = 0x07, init: int = 0x00) -> int:
    crc = init
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc

def decompress_file(input_path, output_path):
    with open(input_path, "rb") as fin:
        expected_crc32 = int.from_bytes(fin.read(CRC32_SIZE), byteorder="little")
        hash_data = fin.read()

    print(f"[INFO] Expected CRC32: {hex(expected_crc32)}")
    hash_blocks = list(hash_data)

    # Precompute possible values for each CRC8 hash
    print("[INFO] Precomputing CRC8 candidates...")
    crc8_table = {i: [] for i in range(256)}
    for b1 in range(256):
        for b2 in range(256):
            block = bytes([b1, b2])
            crc = crc8(block)
            crc8_table[crc].append(block)

    attempt = 0
    while True:
        print(f"\n[TRY #{attempt}] Attempting decompression...")

        decompressed = bytearray()
        for index, h in enumerate(hash_blocks):
            candidates = crc8_table[h]
            chosen = random.choice(candidates)
            decompressed.extend(chosen)

        actual_crc32 = zlib.crc32(decompressed)
        print(f"[INFO] Actual CRC32: {hex(actual_crc32)}")

        if actual_crc32 == expected_crc32:
            print("[✓] CRC32 matched! Writing decompressed output.")
            with open(output_path, "wb") as fout:
                fout.write(decompressed)
            break
        else:
            print("[×] CRC32 mismatch, retrying...\n")
            attempt += 1

def main():
    parser = argparse.ArgumentParser(description="Enpakk — CRC-8 Random Decompressor with CRC32 verification")
    parser.add_argument("input", help="Input .enpakk archive")
    parser.add_argument("output", help="Output file")
    args = parser.parse_args()
    decompress_file(args.input, args.output)

if __name__ == "__main__":
    main()
