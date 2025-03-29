import argparse
import os
import itertools
import random

BLOCK_SIZE = 2  # original data block is 2 bytes
HASH_SIZE = 1   # 1 byte CRC-8 hash

# CRC-8 function (polynomial 0x07)
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
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        block_index = 0
        while True:
            hash_byte = fin.read(HASH_SIZE)
            if not hash_byte:
                break
            target_crc = hash_byte[0]
            print(f"[+] Decompressing block {block_index} - CRC8: {target_crc}...")

            # Collect all matching candidates
            candidates = []
            for b1 in range(256):
                for b2 in range(256):
                    block = bytes([b1, b2])
                    if crc8(block) == target_crc:
                        candidates.append(block)

            if not candidates:
                raise ValueError(f"No matches for CRC8: {target_crc}")

            # Pick one candidate at random
            chosen = random.choice(candidates)
            fout.write(chosen)
            print(f"    ✓ Block {block_index} guessed: {list(chosen)} from {len(candidates)} possibilities")
            block_index += 1

def main():
    parser = argparse.ArgumentParser(description="Enpakk — Random CRC-8 Decompressor for 2-byte blocks")
    parser.add_argument("input", help="Input .enpakk archive")
    parser.add_argument("output", help="Output file")
    args = parser.parse_args()
    decompress_file(args.input, args.output)

if __name__ == "__main__":
    main()
