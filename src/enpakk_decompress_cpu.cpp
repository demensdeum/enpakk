#include <iostream>
#include <fstream>
#include <vector>
#include <unordered_map>
#include <random>
#include <zlib.h> // for crc32
#include <cstring>

// constexpr size_t BLOCK_SIZE = 2; // 2 bytes = 16 bits
// constexpr size_t HASH_SIZE = 1;  // 1 byte = CRC-8
constexpr size_t CRC32_SIZE = 4; // 4 bytes

uint8_t crc8(const std::vector<uint8_t>& data, uint8_t poly = 0x07, uint8_t init = 0x00) {
    uint8_t crc = init;
    for (auto byte : data) {
        crc ^= byte;
        for (int i = 0; i < 8; ++i) {
            if (crc & 0x80)
                crc = (crc << 1) ^ poly;
            else
                crc <<= 1;
        }
    }
    return crc;
}

int main(int argc, char* argv[]) {
    bool verbose = false;
    std::string input_path, output_path;

    // Parse args
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--verbose") == 0) {
            verbose = true;
        } else if (input_path.empty()) {
            input_path = argv[i];
        } else if (output_path.empty()) {
            output_path = argv[i];
        }
    }

    if (input_path.empty() || output_path.empty()) {
        std::cerr << "Usage: " << argv[0] << " [--verbose] input.enpakk output.raw\n";
        return 1;
    }

    std::ifstream fin(input_path, std::ios::binary);
    if (!fin) {
        std::cerr << "Failed to open input file.\n";
        return 1;
    }

    uint32_t expected_crc32;
    fin.read(reinterpret_cast<char*>(&expected_crc32), CRC32_SIZE);

    std::vector<uint8_t> hash_data((std::istreambuf_iterator<char>(fin)), std::istreambuf_iterator<char>());

    if (verbose) {
        std::cout << "[INFO] Expected CRC32: 0x" << std::hex << expected_crc32 << std::dec << "\n";
        std::cout << "[INFO] Precomputing CRC8 table...\n";
    }

    std::unordered_map<uint8_t, std::vector<std::vector<uint8_t>>> crc8_table;
    for (int b1 = 0; b1 < 256; ++b1) {
        for (int b2 = 0; b2 < 256; ++b2) {
            std::vector<uint8_t> block = { static_cast<uint8_t>(b1), static_cast<uint8_t>(b2) };
            uint8_t crc = crc8(block);
            crc8_table[crc].push_back(block);
        }
    }

    std::random_device rd;
    std::mt19937 gen(rd());
    size_t attempt = 0;

    while (true) {
        if (verbose) {
            std::cout << "\n[TRY #" << attempt << "] Decompressing...\n";
        }

        std::vector<uint8_t> decompressed;

        for (size_t i = 0; i < hash_data.size(); ++i) {
            uint8_t h = hash_data[i];
            const auto& candidates = crc8_table[h];
            std::uniform_int_distribution<> dis(0, candidates.size() - 1);
            const auto& chosen = candidates[dis(gen)];
            decompressed.insert(decompressed.end(), chosen.begin(), chosen.end());
        }

        uint32_t actual_crc = crc32(0, decompressed.data(), decompressed.size());

        if (verbose) {
            std::cout << "[INFO] Actual CRC32: 0x" << std::hex << actual_crc << std::dec << "\n";
        }

        if (actual_crc == expected_crc32) {
            std::ofstream fout(output_path, std::ios::binary);
            fout.write(reinterpret_cast<char*>(decompressed.data()), decompressed.size());
            std::cout << "[✓] Decompression successful. Output written to " << output_path << "\n";
            break;
        }

        attempt++;
    }

    return 0;
}
