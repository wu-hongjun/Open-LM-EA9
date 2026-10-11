#!/usr/bin/env python3
"""Offline only: combine the AF template with a validated Mac-prepared profile.

This uses the current reconciled 2.2 template and performs no USB operations.
The native app independently admits only its bundled digest-pinned templates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("profile_image", type=Path, help="Metadata image made by ea9ctl prepare")
parser.add_argument("output", type=Path, help="New AF image; never overwritten")
args = parser.parse_args()
af = ROOT / "firmware/ea9/build/reconciled/ea9-af-reconciled-template.bin"
manifest = json.loads(af.with_suffix(".manifest.json").read_text())
template = af.read_bytes()
metadata = (ROOT / "apps/macos/Sources/DeviceKit/Resources/ea9-profile-template.bin").read_bytes()
source = args.profile_image.read_bytes()
if len(template) != 0x5000 or manifest["profileAddress"] != 0x9f00 or len(source) != 0x5100 or len(metadata) != 0x5100:
    raise SystemExit("Unexpected application/profile layout.")
if hashlib.sha256(template).hexdigest() != manifest["templateSHA256"] or template[-256:] != bytes(256):
    raise SystemExit("AF template does not match its build manifest.")
if source[:-256] != metadata[:-256]:
    raise SystemExit("Input must use the current metadata template; prepare it locally with ea9ctl.")
profile = source[-256:]
if profile[:8] != b"EA9LENS1" or struct.unpack_from("<HH", profile, 8) != (1, 256):
    raise SystemExit("Unsupported profile header.")
if zlib.crc32(profile[:252]) != struct.unpack_from("<I", profile, 252)[0]:
    raise SystemExit("Profile CRC mismatch.")
image = template[:-256] + profile
output_manifest = args.output.with_suffix(".manifest.json")
if args.output.exists() or output_manifest.exists():
    raise SystemExit("Output image and manifest must both be new paths.")
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("xb") as stream:
    stream.write(image)
evidence = {
    "variant": "reconciled-af", "status": "offline-personalized-candidate",
    "imageSHA256": hashlib.sha256(image).hexdigest(), "templateSHA256": manifest["templateSHA256"],
    "profileSHA256": hashlib.sha256(profile).hexdigest(), "bytes": len(image),
    "profileID": profile[24:104].split(b"\0", 1)[0].decode("ascii"),
    "lensName": profile[104:168].split(b"\0", 1)[0].decode("ascii"),
    "proposedLoaderVersion": manifest["proposedLoaderVersion"],
    "motorMotionEnabled": True, "cameraQualified": False, "usbReportsSent": 0,
}
with output_manifest.open("x") as stream:
    json.dump(evidence, stream, indent=2)
    stream.write("\n")
print(f"Prepared {evidence['lensName']} AF candidate, SHA-256 {evidence['imageSHA256']}; no USB reports sent.")
