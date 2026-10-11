"""Input/output guards and portable host-library compilation; no device APIs."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_FIRMWARE = ROOT / "firmware/recovery/stock-1.8.0/application.bin"
FIRMWARE_SHA256 = "f4d616d2ae685775efff0eedbbbaec81d5c922a2f463bb630df83c41be13f564"
FIRMWARE_SIZE = 20172


@dataclass(frozen=True)
class Configuration:
    firmware: Path
    rom: bytes
    output: Path
    compiler: str
    library_suffix: str
    library_flags: tuple


_configuration = None


def read_firmware(path):
    """Only the exact retained stock application is a supported oracle."""
    path = Path(path).expanduser().resolve()
    if path.stat().st_size != FIRMWARE_SIZE:
        raise ValueError("oracle must be the 20,172-byte stock 1.8.0 application")
    rom = path.read_bytes()
    if hashlib.sha256(rom).hexdigest() != FIRMWARE_SHA256:
        raise ValueError("oracle SHA-256 does not match pinned stock 1.8.0")
    return path, rom


def configure(firmware=DEFAULT_FIRMWARE, output=None, compiler=None):
    global _configuration
    if _configuration is not None:
        raise RuntimeError("validation is already configured; start a new process")
    firmware, rom = read_firmware(firmware)
    compiler = compiler or os.environ.get("CC", "clang")
    resolved_compiler = shutil.which(compiler)
    if not resolved_compiler:
        raise ValueError("C compiler is unavailable: " + compiler)
    if sys.platform == "darwin":
        suffix, flags = ".dylib", ("-dynamiclib",)
    elif sys.platform.startswith("linux"):
        suffix, flags = ".so", ("-shared", "-fPIC")
    else:
        raise ValueError("the validation runner supports macOS and Linux")
    if output is None:
        output = Path(tempfile.mkdtemp(prefix="ea9-stock-model-"))
    else:
        output = Path(output).expanduser().resolve()
        # Existing evidence, including an empty directory, is never overwritten.
        output.mkdir(mode=0o700, parents=False, exist_ok=False)
    _configuration = Configuration(
        firmware, rom, output, resolved_compiler, suffix, flags
    )
    return _configuration


def get_configuration():
    return _configuration or configure()


def compile_library(source, name, *, strict=True):
    cfg = get_configuration()
    destination = cfg.output / (name + cfg.library_suffix)
    command = [cfg.compiler, "-std=c11", "-O2"]
    if strict:
        command += ["-Wall", "-Wextra", "-Werror", "-pedantic"]
    command += list(cfg.library_flags)
    command += ["-I", str(HERE), str(source), "-o", str(destination)]
    subprocess.run(command, check=True)
    return destination
