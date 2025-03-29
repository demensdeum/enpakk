# Makefile for Enpakk Decompressor (C++ and C versions)

CXX = clang++
CC = clang
CXXFLAGS = -O3 -std=c++11 -Wall -Wextra -march=native
CFLAGS = -O3 -std=c99 -Wall -Wextra -march=native

LDFLAGS = -lz

TARGET_CPP = enpakk_decompress_cpp
TARGET_C = enpakk_decompress_c

SRC_CPP = enpakk_decompress_cpu.cpp
SRC_C = enpakk_decompress.c

all: $(TARGET_CPP) $(TARGET_C)

$(TARGET_CPP): $(SRC_CPP)
	$(CXX) $(CXXFLAGS) -o $@ $^ $(LDFLAGS)

$(TARGET_C): $(SRC_C)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

clean:
	rm -f $(TARGET_CPP) $(TARGET_C)
