import Foundation
import Metal
import MetalKit
import zlib

let BLOCK_SIZE = 2
let CRC32_SIZE = 4
let MAX_CANDIDATES = 300

func crc8(_ data: [UInt8]) -> UInt8 {
    var crc: UInt8 = 0x00
    for byte in data {
        crc ^= byte
        for _ in 0..<8 {
            if (crc & 0x80) != 0 {
                crc = ((crc << 1) ^ 0x07) & 0xFF
            } else {
                crc = (crc << 1) & 0xFF
            }
        }
    }
    return crc
}

func readFileBytes(path: String) throws -> [UInt8] {
    let data = try Data(contentsOf: URL(fileURLWithPath: path))
    return [UInt8](data)
}

func writeFileBytes(path: String, bytes: [UInt8]) throws {
    let url = URL(fileURLWithPath: path)
    try Data(bytes).write(to: url)
}

func crc32Hash(data: [UInt8]) -> UInt32 {
    return data.withUnsafeBytes { rawBuffer in
        UInt32(crc32(0, rawBuffer.bindMemory(to: Bytef.self).baseAddress, uInt(data.count)))
    }
}

func runMetalDecompressor(
    device: MTLDevice,
    hashData: [UInt8],
    candidates: [UInt8],
    counts: [UInt32],
    expectedCRC: UInt32
) -> [UInt8]? {
    let commandQueue = device.makeCommandQueue()!
    let library = try! device.makeDefaultLibrary(bundle: .main)
    let function = library.makeFunction(name: "bruteForceDecompress")!
    let pipeline = try! device.makeComputePipelineState(function: function)

    let hashLen = UInt32(hashData.count)
    let outputLen = hashData.count * BLOCK_SIZE

    let hashBuffer = device.makeBuffer(bytes: hashData, length: hashData.count)!
    let candidateBuffer = device.makeBuffer(bytes: candidates, length: candidates.count)!
    let countBuffer = device.makeBuffer(bytes: counts, length: counts.count * 4)!
    let hashLenBuf = device.makeBuffer(bytes: [hashLen], length: 4)!
    let expectedBuf = device.makeBuffer(bytes: [expectedCRC], length: 4)!
    let resultBuffer = device.makeBuffer(length: outputLen)!
    let foundFlagBuf = device.makeBuffer(length: 4)!
    memset(foundFlagBuf.contents(), 0, 4)

    while true {
        let commandBuffer = commandQueue.makeCommandBuffer()!
        let encoder = commandBuffer.makeComputeCommandEncoder()!
        encoder.setComputePipelineState(pipeline)

        encoder.setBuffer(hashBuffer, offset: 0, index: 0)
        encoder.setBuffer(candidateBuffer, offset: 0, index: 1)
        encoder.setBuffer(countBuffer, offset: 0, index: 2)
        encoder.setBuffer(hashLenBuf, offset: 0, index: 3)
        encoder.setBuffer(expectedBuf, offset: 0, index: 4)
        encoder.setBuffer(resultBuffer, offset: 0, index: 5)
        encoder.setBuffer(foundFlagBuf, offset: 0, index: 6)

        let gridSize = MTLSize(width: 8192, height: 1, depth: 1)
        let threadGroupSize = MTLSize(width: pipeline.maxTotalThreadsPerThreadgroup, height: 1, depth: 1)
        encoder.dispatchThreads(gridSize, threadsPerThreadgroup: threadGroupSize)

        encoder.endEncoding()
        commandBuffer.commit()
        commandBuffer.waitUntilCompleted()

        let found = foundFlagBuf.contents().load(as: UInt32.self)
        if found == 1 {
            let ptr = resultBuffer.contents().bindMemory(to: UInt8.self, capacity: outputLen)
            return Array(UnsafeBufferPointer(start: ptr, count: outputLen))
        }
    }
}

func main() {
    let args = CommandLine.arguments

    guard args.count >= 3 else {
        print("Usage: \(args[0]) <input.enpakk> <output> [--verbose]")
        exit(1)
    }

    let inputPath = args[1]
    let outputPath = args[2]
    let verbose = args.count >= 4 && args[3] == "--verbose"

    guard let fileBytes = try? readFileBytes(path: inputPath), fileBytes.count > CRC32_SIZE else {
        print("Failed to read input file or file too short.")
        exit(1)
    }

    let expectedCRC = UInt32(fileBytes[0]) |
                      (UInt32(fileBytes[1]) << 8) |
                      (UInt32(fileBytes[2]) << 16) |
                      (UInt32(fileBytes[3]) << 24)

    let hashData = Array(fileBytes[CRC32_SIZE...])

    if verbose {
        print("[INFO] Expected CRC32: 0x\(String(format: "%08X", expectedCRC))")
        print("[INFO] Precomputing CRC8 candidates...")
    }

    var candidates = Array(repeating: [[UInt8]](), count: 256)

    for b1 in 0..<256 {
        for b2 in 0..<256 {
            let block = [UInt8(b1), UInt8(b2)]
            let hash = Int(crc8(block))
            if candidates[hash].count < MAX_CANDIDATES {
                candidates[hash].append(block)
            }
        }
    }

    let metal = MTLCreateSystemDefaultDevice()!

    let candidateFlat = candidates.flatMap { row -> [UInt8] in
        var blocks = row.flatMap { $0 }
        if blocks.count < MAX_CANDIDATES * 2 {
            blocks += Array(repeating: 0, count: MAX_CANDIDATES * 2 - blocks.count)
        }
        return blocks
    }

    let countTable: [UInt32] = candidates.map { UInt32($0.count) }

    if let decompressed = runMetalDecompressor(
        device: metal,
        hashData: hashData,
        candidates: candidateFlat,
        counts: countTable,
        expectedCRC: expectedCRC
    ) {
        try! writeFileBytes(path: outputPath, bytes: decompressed)
        print("[✓] Decompression successful with Metal!")
    } else {
        print("[!] Failed to decompress.")
    }
}

main()
