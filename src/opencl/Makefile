# Compiler
CC = clang

# Paths
OPENCL_HEADERS = /opt/homebrew/Cellar/opencl-headers/2024.10.24/include/

# Flags
CFLAGS = -O2 -Wall -std=c11 -I$(OPENCL_HEADERS)
LDFLAGS = -framework OpenCL -lz

# Targets
TARGET = enpakk_gpu
SRC = main.c

# Default rule
all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Clean rule
clean:
	rm -f $(TARGET)
