import argparse
import os

BLOCK_SIZE = 1  # 1 byte
HASH_SIZE = 1   # 1 byte hash from CRC-8

# Same CRC-8 function as used in compressor
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
            # Brute-force search for the original 1-byte block
            for value in range(256):
                block = bytes([value])
                if crc8(block) == target_crc:
                    fout.write(block)
                    print(f"    ✓ Block {block_index} recovered: {value}")
                    break
            else:
                raise ValueError(f"Failed to find block matching CRC8: {target_crc}")
            block_index += 1

def main():
    parser = argparse.ArgumentParser(description="Enpakk — CRC-8 Byte Decompressor")
    parser.add_argument("input", help="Input .enpakk archive")
    parser.add_argument("output", help="Output file")
    args = parser.parse_args()
    decompress_file(args.input, args.output)

if __name__ == "__main__":
    main()
