import argparse
import os
import zlib  # For CRC32

BLOCK_SIZE = 2  # 16-bit block
HASH_SIZE = 1   # 8-bit CRC8 output

# CRC-8 implementation (poly 0x07, init 0x00)
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

def compress_file(input_path, output_path):
    compressed_data = bytearray()

    with open(input_path, "rb") as fin:
        original_data = fin.read()

    # Compute CRC32 of original uncompressed data
    crc32 = zlib.crc32(original_data)

    # Compress in 2-byte blocks
    for i in range(0, len(original_data), BLOCK_SIZE):
        block = original_data[i:i + BLOCK_SIZE]
        if len(block) < BLOCK_SIZE:
            block = block.ljust(BLOCK_SIZE, b'\x00')  # pad to full block
        h = crc8(block)
        compressed_data.append(h)

    with open(output_path, "wb") as fout:
        fout.write(crc32.to_bytes(4, byteorder="little"))  # Write CRC32 first
        fout.write(compressed_data)  # Then the compressed data

def main():
    parser = argparse.ArgumentParser(description="Enpakk — CRC-8 Compressor with leading CRC32 (original data)")
    subparsers = parser.add_subparsers(dest="command")

    compress_parser = subparsers.add_parser("compress", help="Compress using CRC-8 (2-byte blocks → 1-byte hash)")
    compress_parser.add_argument("input", help="Input file")
    compress_parser.add_argument("output", help="Output .enpakk archive")

    args = parser.parse_args()

    if args.command == "compress":
        compress_file(args.input, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
