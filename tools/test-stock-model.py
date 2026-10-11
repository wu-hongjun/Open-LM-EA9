#!/usr/bin/env python3
"""Offline regression checks for the public stock-model input/output guards."""
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/stock-1.8"))
import config


class InputAndEvidenceGuards(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="ea9-model-guard-test-")
        self.directory = Path(self.workspace.name)
        self.output = self.directory / "new-results"
        config._configuration = None

    def tearDown(self):
        config._configuration = None
        self.workspace.cleanup()

    def test_public_oracle_has_expected_identity(self):
        path, data = config.read_firmware(config.DEFAULT_FIRMWARE)
        self.assertEqual(path, config.DEFAULT_FIRMWARE)
        self.assertEqual(len(data), 20172)
        self.assertEqual(hashlib.sha256(data).hexdigest(), config.FIRMWARE_SHA256)

    def test_same_length_tampered_image_rejected_without_output_or_input_changes(self):
        data = bytearray(config.DEFAULT_FIRMWARE.read_bytes())
        data[1024] ^= 1
        source = self.directory / "wrong.bin"
        source.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            config.configure(source, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(source.read_bytes(), data)

    def test_truncated_image_rejected_without_creating_output(self):
        source = self.directory / "short.bin"
        source.write_bytes(config.DEFAULT_FIRMWARE.read_bytes()[:-1])
        with self.assertRaisesRegex(ValueError, "20,172-byte"):
            config.configure(source, self.output)
        self.assertFalse(self.output.exists())

    def test_existing_evidence_directory_preserved(self):
        self.output.mkdir()
        prior = self.output / "prior.json"
        prior.write_bytes(b'{"preserve":true}\n')
        with self.assertRaises(FileExistsError):
            config.configure(output=self.output, compiler=sys.executable)
        self.assertEqual(prior.read_bytes(), b'{"preserve":true}\n')
        self.assertEqual(list(self.output.iterdir()), [prior])

    def test_existing_empty_output_directory_rejected(self):
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            config.configure(output=self.output, compiler=sys.executable)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_missing_output_parent_is_not_created(self):
        self.output = self.directory / "absent-parent" / "new-results"
        with self.assertRaises(FileNotFoundError):
            config.configure(output=self.output, compiler=sys.executable)
        self.assertFalse(self.output.parent.exists())

    def test_missing_compiler_rejected_before_output(self):
        with self.assertRaisesRegex(ValueError, "compiler is unavailable"):
            config.configure(output=self.output, compiler="ea9-does-not-exist-cc")
        self.assertFalse(self.output.exists())

    def test_new_output_can_be_created_only_once(self):
        configured = config.configure(output=self.output, compiler=sys.executable)
        self.assertEqual(configured.output, self.output.resolve())
        self.assertTrue(self.output.is_dir())
        with self.assertRaises(RuntimeError):
            config.configure(output=self.directory / "second", compiler=sys.executable)
        self.assertFalse((self.directory / "second").exists())

    def test_optimized_python_cannot_skip_fixture_assertions(self):
        completed = subprocess.run(
            [sys.executable, "-O", str(ROOT / "research/stock-1.8/run.py"),
             "--output", str(self.output)], text=True, capture_output=True
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("fixture assertions must stay enabled", completed.stderr)
        self.assertFalse(self.output.exists())

    def test_promoted_model_bytes_preserve_original_authored_model(self):
        expected = {
            "stock_model.c": "73857edba47e37670214b269770697cf5b0108ac9bf55638a24489394703f815",
            "stock_model.h": "ed572052599a89e1c0c3e1597d4548fc25f8f9b3d2a635f632f6a88026f146b2",
        }
        for name, digest in expected.items():
            self.assertEqual(hashlib.sha256((config.HERE / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
