#!/bin/bash

python3 enpakk_compress.py compress test.txt compressed.enpakk
#python3 enpakk_decompress_cpu.py compressed.enpakk uncompressed.txt

make clean
make
#./enpakk_decompress_cpp compressed.enpakk uncompressed.txt
./enpakk_decompress_c compressed.enpakk uncompressed.txt