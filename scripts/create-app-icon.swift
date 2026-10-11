import AppKit

// Native SF Symbol artwork; deterministic local generation, no downloaded image assets.
let directory = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
let canvas = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1024, pixelsHigh: 1024, bitsPerSample: 8,
                             samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: canvas)
let shape = NSBezierPath(roundedRect: NSRect(x: 80, y: 80, width: 864, height: 864), xRadius: 195, yRadius: 195)
shape.addClip()
NSGradient(starting: NSColor(srgbRed: 0.08, green: 0.20, blue: 0.44, alpha: 1),
           ending: NSColor(srgbRed: 0.20, green: 0.55, blue: 0.72, alpha: 1))!.draw(in: shape, angle: 55)
let symbol = NSImage(systemSymbolName: "camera.aperture", accessibilityDescription: nil)!
    .withSymbolConfiguration(NSImage.SymbolConfiguration(paletteColors: [.white]))!
symbol.draw(in: NSRect(x: 250, y: 250, width: 524, height: 524))
NSGraphicsContext.restoreGraphicsState()
let source = canvas.cgImage!
for points in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let size = points * scale
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: size, pixelsHigh: size, bitsPerSample: 8,
                                     samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
        let context = NSGraphicsContext(bitmapImageRep: bitmap)!.cgContext
        context.interpolationQuality = .high
        context.draw(source, in: CGRect(x: 0, y: 0, width: size, height: size))
        let name = "icon_\(points)x\(points)\(scale == 2 ? "@2x" : "").png"
        try bitmap.representation(using: .png, properties: [:])!.write(to: directory.appendingPathComponent(name))
    }
}
