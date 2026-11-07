import AppKit

// OpenLensAdapter app icon generator.
// Usage: swift scripts/create-app-icon.swift OUTPUT.iconset
// Deterministic vector artwork: two concentric mount rings joined by three bayonet lugs.

guard CommandLine.arguments.count >= 2 else {
    FileHandle.standardError.write("usage: swift create-app-icon.swift OUTPUT.iconset\n".data(using: .utf8)!)
    exit(1)
}

let outputURL = URL(fileURLWithPath: CommandLine.arguments[1], isDirectory: true)
do {
    try FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)
} catch {
    FileHandle.standardError.write("error: cannot create \(outputURL.path): \(error)\n".data(using: .utf8)!)
    exit(1)
}

guard let srgb = CGColorSpace(name: CGColorSpace.sRGB) else {
    FileHandle.standardError.write("error: sRGB color space unavailable\n".data(using: .utf8)!)
    exit(1)
}

// MARK: - Helpers

func color(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
    let r = CGFloat((hex >> 16) & 0xFF) / 255
    let g = CGFloat((hex >> 8) & 0xFF) / 255
    let b = CGFloat(hex & 0xFF) / 255
    return CGColor(colorSpace: srgb, components: [r, g, b, alpha])!
}

func gradient(_ stops: [(UInt32, CGFloat)], alpha: CGFloat = 1) -> CGGradient {
    let colors = stops.map { color($0.0, alpha) } as CFArray
    let locations = stops.map { $0.1 }
    return CGGradient(colorsSpace: srgb, colors: colors, locations: locations)!
}

func makeContext(_ px: Int) -> CGContext {
    guard let ctx = CGContext(
        data: nil,
        width: px,
        height: px,
        bitsPerComponent: 8,
        bytesPerRow: 0,
        space: srgb,
        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
    ) else {
        FileHandle.standardError.write("error: cannot create \(px)px bitmap context\n".data(using: .utf8)!)
        exit(1)
    }
    ctx.clear(CGRect(x: 0, y: 0, width: px, height: px))
    ctx.setAllowsAntialiasing(true)
    ctx.setShouldAntialias(true)
    ctx.interpolationQuality = .high
    return ctx
}

let canvas: CGFloat = 1024
let center = CGPoint(x: canvas / 2, y: canvas / 2)

func circle(_ r: CGFloat) -> CGPath {
    CGPath(ellipseIn: CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2), transform: nil)
}

func ring(outer: CGFloat, inner: CGFloat) -> CGPath {
    let p = CGMutablePath()
    p.addPath(circle(outer))
    p.addPath(circle(inner))
    return p
}

/// Native-feeling continuous squircle (superellipse, n = 5) inside the standard 824pt icon grid.
func squircle(halfSize a: CGFloat, exponent n: CGFloat = 5, samples: Int = 720) -> CGPath {
    let p = CGMutablePath()
    for i in 0..<samples {
        let t = CGFloat(i) / CGFloat(samples) * 2 * .pi
        let c = cos(t), s = sin(t)
        let x = a * (c < 0 ? -1 : 1) * pow(abs(c), 2 / n)
        let y = a * (s < 0 ? -1 : 1) * pow(abs(s), 2 / n)
        let pt = CGPoint(x: center.x + x, y: center.y + y)
        if i == 0 { p.move(to: pt) } else { p.addLine(to: pt) }
    }
    p.closeSubpath()
    return p
}

func sector(inner r1: CGFloat, outer r2: CGFloat, centerDegrees: CGFloat, spanDegrees: CGFloat) -> CGPath {
    let mid = centerDegrees * .pi / 180
    let half = spanDegrees * .pi / 360
    let p = CGMutablePath()
    p.addArc(center: center, radius: r2, startAngle: mid - half, endAngle: mid + half, clockwise: false)
    p.addArc(center: center, radius: r1, startAngle: mid + half, endAngle: mid - half, clockwise: true)
    p.closeSubpath()
    return p
}

func fillLinear(_ ctx: CGContext, _ path: CGPath, _ g: CGGradient, from a: CGPoint, to b: CGPoint, evenOdd: Bool = false) {
    ctx.saveGState()
    ctx.addPath(path)
    ctx.clip(using: evenOdd ? .evenOdd : .winding)
    ctx.drawLinearGradient(g, start: a, end: b, options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
    ctx.restoreGState()
}

func stroke(_ ctx: CGContext, _ path: CGPath, _ c: CGColor, width: CGFloat) {
    ctx.saveGState()
    ctx.addPath(path)
    ctx.setStrokeColor(c)
    ctx.setLineWidth(width)
    ctx.setLineJoin(.round)
    ctx.strokePath()
    ctx.restoreGState()
}

// MARK: - Geometry

let tileHalf: CGFloat = 412            // 824pt tile, 100pt transparent margin
let outerRingOuter: CGFloat = 340
let outerRingInner: CGFloat = 268
let innerRingOuter: CGFloat = 228
let innerRingInner: CGFloat = 158
let lugInner: CGFloat = 214
let lugOuter: CGFloat = 288
let lugSpan: CGFloat = 30
let lugAngles: [CGFloat] = [90, 210, 330]

// MARK: - Master render (1024 x 1024, non-flipped, origin bottom-left)

func renderMaster() -> CGImage {
    let ctx = makeContext(Int(canvas))
    let tile = squircle(halfSize: tileHalf)

    // Tile drop shadow (stays within transparent margin).
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -10), blur: 22, color: color(0x000000, 0.32))
    ctx.addPath(tile)
    ctx.setFillColor(color(0x1C1F23))
    ctx.fillPath()
    ctx.restoreGState()

    // Everything else is clipped to the squircle.
    ctx.saveGState()
    ctx.addPath(tile)
    ctx.clip()

    // Charcoal body with a restrained vertical gradient.
    fillLinear(ctx, tile,
               gradient([(0x353A41, 0), (0x24272C, 0.55), (0x15171A, 1)]),
               from: CGPoint(x: center.x, y: center.y + tileHalf),
               to: CGPoint(x: center.x, y: center.y - tileHalf))
    stroke(ctx, tile, color(0xFFFFFF, 0.07), width: 5)

    // Mount body base with soft contact shadow; this also forms the dark gap between rings.
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -14), blur: 30, color: color(0x000000, 0.5))
    ctx.addPath(circle(outerRingOuter))
    ctx.setFillColor(color(0x0C0E11))
    ctx.fillPath()
    ctx.restoreGState()

    // Outer mount ring: brushed silver, lit from upper left.
    let outerRing = ring(outer: outerRingOuter, inner: outerRingInner)
    fillLinear(ctx, outerRing,
               gradient([(0xEEF1F4, 0), (0xB9BEC4, 0.5), (0x6A7078, 1)]),
               from: CGPoint(x: center.x - 250, y: center.y + 250),
               to: CGPoint(x: center.x + 250, y: center.y - 250),
               evenOdd: true)
    stroke(ctx, circle(304), color(0x000000, 0.16), width: 3)          // machined groove
    stroke(ctx, circle(306.5), color(0xFFFFFF, 0.18), width: 1.5)
    stroke(ctx, circle(outerRingOuter - 1), color(0x0A0B0D, 0.55), width: 2)
    stroke(ctx, circle(outerRingInner + 1.5), color(0x24282D, 0.9), width: 3)

    // Inner mount ring: separate part, slightly cooler and darker, lit from above.
    let innerRing = ring(outer: innerRingOuter, inner: innerRingInner)
    ctx.saveGState()
    ctx.setShadow(offset: CGSize(width: 0, height: -6), blur: 14, color: color(0x000000, 0.6))
    ctx.addPath(innerRing)
    ctx.setFillColor(color(0x7C838A))
    ctx.fillPath(using: .evenOdd)
    ctx.restoreGState()
    fillLinear(ctx, innerRing,
               gradient([(0xDCE0E4, 0), (0xA3A9B0, 0.55), (0x5C626A, 1)]),
               from: CGPoint(x: center.x, y: center.y + innerRingOuter),
               to: CGPoint(x: center.x, y: center.y - innerRingOuter),
               evenOdd: true)
    stroke(ctx, circle(innerRingOuter - 1), color(0x0A0B0D, 0.5), width: 2)
    stroke(ctx, circle(innerRingInner + 1.5), color(0x1E2226, 0.9), width: 3)

    // Lens throat: deep glass with a faint, quiet reflection.
    let glass = circle(innerRingInner)
    ctx.saveGState()
    ctx.addPath(glass)
    ctx.clip()
    ctx.drawRadialGradient(
        gradient([(0x26313B, 0), (0x121619, 0.7), (0x08090B, 1)]),
        startCenter: CGPoint(x: center.x - 34, y: center.y + 44), startRadius: 0,
        endCenter: center, endRadius: innerRingInner,
        options: [.drawsAfterEndLocation])
    let reflection = CGPath(ellipseIn: CGRect(x: center.x - 112, y: center.y + 38, width: 150, height: 82), transform: nil)
    ctx.addPath(reflection)
    ctx.setFillColor(color(0xFFFFFF, 0.06))
    ctx.fillPath()
    ctx.restoreGState()
    stroke(ctx, circle(innerRingInner - 2), color(0x000000, 0.6), width: 4)

    // Bayonet lugs: the single teal accent, bridging inner ring to outer ring.
    for angle in lugAngles {
        let lug = sector(inner: lugInner, outer: lugOuter, centerDegrees: angle, spanDegrees: lugSpan)
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -4), blur: 8, color: color(0x000000, 0.45))
        ctx.addPath(lug)
        ctx.setFillColor(color(0x1A9497))
        ctx.fillPath()
        ctx.restoreGState()

        let box = lug.boundingBox
        fillLinear(ctx, lug,
                   gradient([(0x4CD6CE, 0), (0x1B9C9C, 1)]),
                   from: CGPoint(x: box.midX, y: box.maxY),
                   to: CGPoint(x: box.midX, y: box.minY))
        stroke(ctx, lug, color(0x0B2E30, 0.7), width: 3)
    }

    ctx.restoreGState() // squircle clip

    guard let image = ctx.makeImage() else {
        FileHandle.standardError.write("error: failed to finalize master image\n".data(using: .utf8)!)
        exit(1)
    }
    return image
}

// MARK: - Downsampling (successive 2x reductions for clean, box-like filtering)

func halve(_ image: CGImage) -> CGImage {
    let px = max(1, image.width / 2)
    let ctx = makeContext(px)
    ctx.interpolationQuality = .high
    ctx.draw(image, in: CGRect(x: 0, y: 0, width: px, height: px))
    guard let out = ctx.makeImage() else {
        FileHandle.standardError.write("error: failed to downsample to \(px)px\n".data(using: .utf8)!)
        exit(1)
    }
    return out
}

let master = renderMaster()
var images: [Int: CGImage] = [1024: master]
var current = master
while current.width > 16 {
    current = halve(current)
    images[current.width] = current
}

// MARK: - Write iconset

let points = [16, 32, 128, 256, 512]
let scales = [1, 2]

for pt in points {
    for scale in scales {
        let px = pt * scale
        guard let image = images[px] else {
            FileHandle.standardError.write("error: missing \(px)px rendition\n".data(using: .utf8)!)
            exit(1)
        }
        let rep = NSBitmapImageRep(cgImage: image)
        rep.size = NSSize(width: pt, height: pt)
        guard let data = rep.representation(using: .png, properties: [:]) else {
            FileHandle.standardError.write("error: PNG encoding failed for \(px)px\n".data(using: .utf8)!)
            exit(1)
        }
        let name = scale == 1 ? "icon_\(pt)x\(pt).png" : "icon_\(pt)x\(pt)@2x.png"
        do {
            try data.write(to: outputURL.appendingPathComponent(name), options: .atomic)
        } catch {
            FileHandle.standardError.write("error: cannot write \(name): \(error)\n".data(using: .utf8)!)
            exit(1)
        }
    }
}

print("Wrote OpenLensAdapter iconset to \(outputURL.path)")