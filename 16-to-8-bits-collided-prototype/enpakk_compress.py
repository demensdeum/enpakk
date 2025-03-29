import argparse
import os

BLOCK_SIZE = 2  # 16-bit block
HASH_SIZE = 1   # 8-bit hash output (CRC-8)

# Simple CRC-8 implementation (polynomial 0x07, initial 0x00)
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
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        while block := fin.read(BLOCK_SIZE):
            if len(block) < BLOCK_SIZE:
                block = block.ljust(BLOCK_SIZE, b'\x00')  # Pad to full block
            h = crc8(block)
            fout.write(h.to_bytes(HASH_SIZE, byteorder="little"))

def main():
    parser = argparse.ArgumentParser(description="Enpakk — CRC-8 Compressor (2-byte blocks → 1-byte hash)")
    subparsers = parser.add_subparsers(dest="command")

    compress_parser = subparsers.add_parser("compress", help="Compress using CRC-8 (2-byte blocks)")
    compress_parser.add_argument("input", help="Input file")
    compress_parser.add_argument("output", help="Output .enpakk archive")

    args = parser.parse_args()

    if args.command == "compress":
        compress_file(args.input, args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
