#!/bin/bash

make clean
make

python3 ../enpakk_compress.py compress ../test.txt ../compressed.enpakk

while true; do
    ./enpakk_gpu ../compressed.enpakk uncompressed.txt

    if cmp -s "uncompressed.txt" "../test.txt"; then
        echo "Files match!"
        break
    else
        echo "Content of ../test.txt:"
        cat ../test.txt
        echo ""

        echo "Content of ../uncompressed.txt:"
        cat ../uncompressed.txt
        echo ""
        
        echo "Files don't match, retrying..."
        echo -n "CRC32 uncompressed.txt: "
        crc32 ../test.txt
        echo -n "CRC32 compressed.enpakk: "
        crc32 ../test.txt
        echo ""

        exit 0
    fi
done
