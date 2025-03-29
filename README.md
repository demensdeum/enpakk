# 🌀 Enpakk — Enthropy Pack Kompressor

**Enpakk** is not your typical compression tool.

It doesn't compress files by removing redundancy.  
It doesn't store your data at all.

Instead, **Enpakk splits a file into 32-byte blocks, stores only their MD5 hashes**, and during "decompression," it attempts to reconstruct the original file using **brute-force random guessing**, validating each block against the stored hash.

Welcome to the world's first **hash-only, entropy-based stochastic compressor**.

---

## 📦 What It Does

- 🧠 **Compress**: Split the file into 32-byte blocks. For each block, compute and store the MD5 hash. That’s it. No actual data is stored.
- 🎲 **Decompress**: For each stored MD5 hash, generate random 32-byte blocks until one matches the hash. Output it. Repeat.

> Warning: Decompression is... *theoretically possible*. In practice, it's a cosmic lottery.

---

## 🔧 Usage

```bash
# Compress a file into a .enpakk archive
python enpakk.py compress input.bin archive.enpakk

# Decompress (via random guessing until match is found)
python enpakk.py decompress archive.enpakk output.bin
