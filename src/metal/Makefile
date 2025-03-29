# Makefile for EnpakkSwiftDecompressor

PROJECT_NAME=EnpakkSwiftDecompressor
BUILD_DIR=.build/release
EXECUTABLE=$(BUILD_DIR)/$(PROJECT_NAME)

all: build

build:
	swift build -c release

run: build
	$(EXECUTABLE) input.enpakk output.bin --verbose

clean:
	swift package clean
	rm -rf $(BUILD_DIR)

open:
	open Package.swift
