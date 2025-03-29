import argparse
import hashlib
import os
import random
from multiprocessing import Pool, cpu_count

BLOCK_SIZE = 3

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

def decompress_block_parallel(md5: bytes, max_attempts: int, workers: int = cpu_count()):
    print(f"    🧠 Brute-forcing with {workers} workers...")
    with Pool(processes=workers) as pool:
        for attempt_start in range(0, max_attempts, workers):
            tasks = [md5] * workers
            results = pool.starmap(try_match_block, zip(tasks, range(workers)))
            for result in results:
                if result is not None:
                    return result
    raise ValueError("Decompression failed: no match found.")

def decompress_file(input_path, output_path, max_attempts=10**8):
    from multiprocessing import cpu_count
    with open(input_path, "rb") as fin, open(output_path, "wb") as fout:
        block_index = 0
        while md5 := fin.read(16):
            print(f"[+] Decompressing block {block_index}...")
            block = decompress_block_parallel(md5, max_attempts, workers=cpu_count())
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
