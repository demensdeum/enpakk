# Compiler
CC = clang

# Paths
OPENCL_HEADERS = /opt/homebrew/Cellar/opencl-headers/2024.10.24/include/

# Optimization Flags
CFLAGS = -O3 -Wall -Wextra -march=native -std=c11 -flto -I$(OPENCL_HEADERS)
LDFLAGS = -framework OpenCL -lz -flto

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
