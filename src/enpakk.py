import argparse
import hashlib
import os
import random

BLOCK_SIZE = 3

def compress_file(input_path, output_path):
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        while block := fin.read(BLOCK_SIZE):
            md5 = hashlib.md5(block).digest()
            fout.write(md5)

def decompress_file(input_path, output_path, max_attempts=10**8):
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        block_index = 0
        while md5 := fin.read(16):
            print(f"[+] Decompressing block {block_index}...")
            for attempt in range(max_attempts):
                candidate = os.urandom(BLOCK_SIZE)
                if hashlib.md5(candidate).digest() == md5:
                    fout.write(candidate)
                    print(f"    ✓ Found match after {attempt + 1} attempts")
                    break
            else:
                print(f"    ✗ Failed to find match after {max_attempts} attempts")
                raise ValueError("Decompression failed for a block.")
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
