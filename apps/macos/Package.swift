// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "OpenLensAdapter",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "OpenLensAdapter", targets: ["OpenLensAdapter"]),
        .executable(name: "ea9ctl", targets: ["EA9CLI"])
    ],
    targets: [
        .target(name: "LensCore", resources: [.process("Resources")]),
        .target(name: "DeviceKit", dependencies: ["LensCore"], resources: [.process("Resources")], linkerSettings: [.linkedFramework("IOKit")]),
        .executableTarget(name: "OpenLensAdapter", dependencies: ["LensCore", "DeviceKit"], resources: [.process("Resources")]),
        .executableTarget(name: "EA9CLI", dependencies: ["DeviceKit", "LensCore"]),
        .testTarget(name: "LensCoreTests", dependencies: ["LensCore"]),
        .testTarget(name: "DeviceKitTests", dependencies: ["DeviceKit"]),
        .testTarget(name: "AppWorkflowTests", dependencies: ["OpenLensAdapter", "DeviceKit", "LensCore"])
    ]
)
