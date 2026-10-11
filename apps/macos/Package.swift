// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "OpenLMEA9",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "OpenLMEA9", targets: ["OpenLMEA9"]),
        .executable(name: "ea9ctl", targets: ["EA9CLI"])
    ],
    targets: [
        .target(name: "LensCore", resources: [.process("Resources")]),
        .target(name: "DeviceKit", dependencies: ["LensCore"], resources: [.process("Resources")], linkerSettings: [.linkedFramework("IOKit")]),
        .executableTarget(name: "OpenLMEA9", dependencies: ["LensCore", "DeviceKit"], resources: [.process("Resources")]),
        .executableTarget(name: "EA9CLI", dependencies: ["DeviceKit", "LensCore"]),
        .testTarget(name: "LensCoreTests", dependencies: ["LensCore"]),
        .testTarget(name: "DeviceKitTests", dependencies: ["DeviceKit"]),
        .testTarget(name: "AppWorkflowTests", dependencies: ["OpenLMEA9", "DeviceKit", "LensCore"])
    ]
)
