import Foundation
import ImageIO

// Read metadata only; preserve the owner's original image unchanged.
guard CommandLine.arguments.count == 3 else {
    fputs("Usage: swift inspect_camera_metadata.swift INPUT PRIVATE_JSON\n", stderr)
    exit(1)
}
let input = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
guard let source = CGImageSourceCreateWithURL(input as CFURL, nil),
      let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) else {
    fputs("ImageIO could not read image metadata.\n", stderr)
    exit(1)
}
func normalized(_ value: Any) -> Any {
    if let data = value as? Data { return ["base64": data.base64EncodedString(), "bytes": data.count] as [String: Any] }
    if let date = value as? Date { return ISO8601DateFormatter().string(from: date) }
    if let dict = value as? [String: Any] { return dict.mapValues(normalized) }
    if let array = value as? [Any] { return array.map(normalized) }
    if value is String || value is NSNumber || value is NSNull { return value }
    return String(describing: value)
}
let document: [String: Any] = ["reader": "macOS ImageIO", "imageCount": CGImageSourceGetCount(source),
                             "properties": normalized(properties)]
let data = try JSONSerialization.data(withJSONObject: document, options: [.prettyPrinted, .sortedKeys])
try FileManager.default.createDirectory(at: output.deletingLastPathComponent(), withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
try data.write(to: output, options: [.withoutOverwriting])
try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: output.path)
print("Read image metadata into a private report; source image unchanged.")
