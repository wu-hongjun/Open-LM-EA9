#!/usr/bin/env python3
"""Offline diagnostic availability and actual protocol-startup counterexamples.

Uses frozen source copies, inert flash/registers and synthetic pin/tick inputs.
Never accesses hardware or canonical host state; does not build a firmware image.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = ROOT / "artifacts/private/crash41-final"
BASE = ROOT / "artifacts/private/reference40-repeat"
PINS = {
    FROZEN: ("557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b",
             "fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641"),
    BASE: ("8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc",
           "06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae"),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(source):
    manifest = json.loads((source / "manifest.json").read_text())
    manifest_pin, image_pin = PINS[source]
    assert sha(source / "manifest.json") == manifest_pin
    assert sha(source / "contax-zeiss-50-f1-4.bin") == manifest["imageSHA256"] == image_pin
    assert len(manifest["sources"]) == 49
    for name, pin in manifest["sources"].items():
        assert sha(source / name) == pin, name
    assert sha(source / "tools/hosttest/shim.c") == manifest["hostTestShimSHA256"]
    return manifest


def ordered(text, tokens):
    positions = [text.index(token) for token in tokens]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not __debug__:
        raise SystemExit("Python assertions must remain enabled")
    out = args.output.resolve()
    assert out.is_relative_to(ROOT / "artifacts/private")
    candidate = verify(FROZEN)
    verify(BASE)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copytree(FROZEN / "src", out / "src")
    shutil.copytree(FROZEN / "tools/hosttest", out / "host")

    # Verify the caller order whose downstream availability is under review.
    main_source = (FROZEN / "src/main.c").read_text().split("int main(void)\n{", 1)[1]
    ordered(main_source, ["st_crash_boot();", "board_init_pins();", "clock_init();",
                        "delay_init();", "st_watchdog_start();", "em_init();",
                        "abs_encoder_set_reference();", "st_watchdog_arm();", "for (;;) {"])
    old_main = (BASE / "src/main.c").read_text().split("int main(void)\n{", 1)[1]
    ordered(old_main, ["board_init_pins();", "st_init();", "clock_init();", "em_init();"])
    assert "st_crash_boot" not in old_main and "st_boot_record" not in old_main
    flash_source = (FROZEN / "src/startup_trace_flash.c").read_text()
    ordered(flash_source[flash_source.index("void st_crash_boot(void)"):],
            ["motor_emergency_release();", "WDT->CTRL.reg=0;", "st_init();",
             "if (st_boot_record(cause)) st_halt();"])

    # Preserve the production st_fail/watchdog bodies exactly. Hardware primitives
    # (NVM/IRQ and ARM HardFault) are the explicit host boundary, not under test.
    module = flash_source[flash_source.index("void st_fail("):
                          flash_source.index("/* No C prologue,")]
    (out / "terminal.inc").write_text(module)
    shutil.copyfile(HERE / "test_causality.c", out / "test.c")
    sam = out / "host/sam.h"
    sam_text = sam.read_text().replace(
        "struct host_reg8  { uint8_t  reg; };",
        "struct host_reg8 { union { uint8_t reg; struct { unsigned PMUXEN:1; } bit; }; };")
    assert sam_text != sam.read_text()
    sam.write_text(sam_text.replace("#endif", '#include "watchdog_mock.h"\n#endif'))
    shutil.copyfile(HERE / "watchdog_mock.h", out / "host/watchdog_mock.h")
    command = ["clang", "-std=gnu11", "-DST_HOST", "-DEA9_NO_LOG", "-O1", "-Wall",
               "-Wextra", "-Werror", "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
               "-I" + str(out), "-I" + str(out / "host"), "-I" + str(out / "src"),
               str(out / "test.c"), str(out / "host/shim.c")]
    command += [str(out / "src" / (name + ".c")) for name in
                ["emount", "emount_packets", "em_frame", "em_owner", "em_shutdown", "motion_trace"]]
    results = {}
    for variant in ["exact", "mutant-ignore-boot-failure"]:
        code = module
        if variant != "exact":
            assert module.count("if (st_boot_record(cause)) st_halt();") == 1
            code = module.replace("if (st_boot_record(cause)) st_halt();", "(void)st_boot_record(cause);")
        (out / "terminal.inc").write_text(code)
        exe = out / variant
        build = subprocess.run(command + ["-o", str(exe)], capture_output=True, text=True, timeout=40)
        assert build.returncode == 0, build.stderr
        cases = ["clean16", "fulltail", "crash-latch", "observed-shape", "stage8",
                 "healthy-shutdown", "availability"] if variant == "exact" else ["clean16", "crash-latch"]
        results[variant] = {}
        for case in cases:
            result = subprocess.run([str(exe), case], capture_output=True, text=True, timeout=15)
            expected = 23 if case == "availability" else 0
            if variant != "exact":
                target = {"clean16": "Assertion failed: (boot())",
                          "crash-latch": "crash boot returned"}[case]
                assert result.returncode != 0 and "Assertion failed" in result.stderr and target in result.stderr, result.stderr
            else:
                assert result.returncode == expected, (case, result.returncode, result.stdout, result.stderr)
            results[variant][case] = {
                "exitCode": result.returncode, "stdout": result.stdout,
                "stderr": result.stderr.replace(str(out), "PRIVATE_OUTPUT")}
    (out / "terminal.inc").write_text(module)

    shutil.copytree(BASE / "src", out / "old-src")
    exe = out / "old40-control"
    build = subprocess.run(["clang", "-std=gnu11", "-DST_HOST", "-O1", "-Wall", "-Wextra", "-Werror",
                            "-fsanitize=address,undefined", "-fno-sanitize-recover=all",
                            "-I" + str(out / "old-src"), str(HERE / "test_old40.c"), "-o", str(exe)],
                           capture_output=True, text=True, timeout=40)
    assert build.returncode == 0, build.stderr
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    results["old40-control"] = {"exitCode": result.returncode, "stdout": result.stdout}
    verify(FROZEN)
    verify(BASE)
    receipt = {
        "status": "offline-behavior-confirmed-availability-requirement-fails",
        "hardwareAccess": False,
        "candidateManifestSHA256": PINS[FROZEN][0], "candidateImageSHA256": candidate["imageSHA256"],
        "baseManifestSHA256": PINS[BASE][0], "baseImageSHA256": PINS[BASE][1],
        "sourcePinsVerifiedBeforeAndAfterPerImage": 49,
        "callerOrderingAsserted": True, "results": results,
        "harnessPins": {p.name: sha(p) for p in HERE.iterdir() if p.suffix in (".py", ".c", ".h")},
        "limits": ["Memory-backed flash and inert registers; no physical elapsed time or pin behavior",
                   "Actual trace C/em_init execute; terminal/watchdog bodies extracted exactly; whole main not executed",
                   "Synthetic slot shape only; no camera frames, operands, identifiers or secrets",
                   "Observed hardware shutter-delay causal attribution remains unresolved"],
    }
    (out / "results.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "results": results}, indent=2))


if __name__ == "__main__":
    main()
