// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "EnpakkSwiftDecompressor",
    platforms: [
        .macOS(.v11)
    ],
    products: [
        .executable(
            name: "EnpakkSwiftDecompressor",
            targets: ["EnpakkSwiftDecompressor"]
        )
    ],
    targets: [
        .executableTarget(
            name: "EnpakkSwiftDecompressor",
            dependencies: [],
            resources: [
                .process("Metal/decompressorKernel.metal")
            ]
        )
    ]
)

