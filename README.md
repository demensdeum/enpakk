# Enpakk — Enthropy Pack Kompressor

**Enpakk** is an experimental entropy-based compressor that transforms each 2-byte block of input into a single byte using CRC-8. To ensure data integrity, a CRC32 checksum of the original uncompressed data is prepended to the compressed file.

Decompression is performed using brute-force random guessing until the reconstructed data's CRC32 matches the original.

⚠️ **Warning**: This is not a real compression algorithm. It’s slow, probabilistic, and meant for research, fun, or CTF-style challenges. Not suitable for production use.

---

## 📦 Features

- Compresses 2-byte blocks into 1-byte CRC-8 hashes
- Adds a CRC32 checksum of the original input (stored at file start)
- Randomized decompression via brute-force search
- Implemented in **Python**, **C++**, and **C**
- C/C++ builds provided via a single `Makefile`

---

## 🔧 Installation

```bash
git clone https://github.com/yourname/enpakk
cd enpakk
```

---

## 🚀 Usage

### Compression

```bash
python enpakk.py compress input.bin output.enpakk
```

- Compresses `input.bin` using CRC-8 block hashing
- Prepends a CRC32 checksum of the original data

### Decompression

```bash
python decompress.py input.enpakk output.bin
```

- Randomly brute-forces 2-byte blocks until the CRC32 of the output matches the one stored in the archive
- Might take seconds or years 😄 — depends on luck and file size

---

## 📚 How it Works

- **Block Size**: 2 bytes (16 bits)
- **Hash Function**: CRC-8 (poly `0x07`)
- **Output per block**: 1 byte
- **Checksum**: CRC32 of the full uncompressed input (stored at the start)

Decompression:
1. Reads the CRC32 from the beginning
2. Guesses each 2-byte block that matches the stored CRC-8
3. Verifies final CRC32; retries if incorrect

---

## 📉 Compression Ratio

| Block | Input Size | Output Size | Compression Ratio |
|-------|------------|-------------|--------------------|
| 2B    | N          | N/2 + 4     | ~50% + 4B header   |

---

## 🌍 Real World Example

Trying to compress the text `"ABC"`:

```bash
echo -n "ABC" > abc.txt
python enpakk.py compress abc.txt abc.enpakk
python decompress.py abc.enpakk result.txt
```

- Decompression is **fast**, as the brute-force space for 3 ASCII characters (6 bytes) is small.
- However, the compressed file (`abc.enpakk`) is **larger** than the original (`abc.txt`) due to the 4-byte CRC32 header + 1.5 bytes (rounded up) for data.

---

## ❗ Limitations

- The **main issue** in the current implementation is **CRC32 collisions** between the original and decompressed data. If a guessed output has the same CRC32 as the original input but different content, it will be falsely accepted as correct.
- Decompression is non-deterministic and becomes **exponentially slower** with larger files.
- Not guaranteed to produce the original data — only something with the same CRC32.

---

## 🧪 Why?

- For fun
- For hacking
- For demonstrating the concept of lossy hash-based compression + verification

---

## ⚠️ Disclaimer

This is **not** practical compression. It’s a CPU-intensive, brute-force method and may take an unreasonable amount of time to decompress. You've been warned 😅

---

## 📜 License

MIT License
