#!/usr/bin/env python3
"""Bind frozen regression templates to 4.0 without editing prior releases/tests.

The reviewed 3.7 binder remains the implementation. Only version, immediate-base
identity and its output label change; fixtures and controls are still hash-bound.
Any intentional production contract change needs a separate explicit adaptation.
"""
import hashlib
import json
from pathlib import Path
from contract_adapters import adapt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
config = json.loads((HERE/'test-inputs.json').read_text())
assert hashlib.sha256((HERE/'contract_adapters.py').read_bytes()).hexdigest() == config['contractAdapterSHA256']
assert hashlib.sha256((HERE/'contract-fixtures.json').read_bytes()).hexdigest() == config['contractFixturePinsSHA256']
previous = HERE.with_name('next37') / 'replay.py'
text = previous.read_text()
assert hashlib.sha256(previous.read_bytes()).hexdigest() == 'ba4b8b98751c0d21edf4a04017376fb4dc0a36245a6c861c065885e123436c0d'
assert text.count("'[3,7,0]'") == 1
text = text.replace("'[3,7,0]'", "'[4,0,0]'")
old = "assert cm['baseImageSHA256'] == 'd8a60e48484d1b48e3aff0da18e6d89453d1284a8b23dca01393b320fdc6651f'"
assert text.count(old) == 1
text = text.replace(old, "assert cm['baseImageSHA256'] == '87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44'")
text = text.replace('passed-bound-37-regression-replay', 'passed-bound-40-regression-replay')
text = text.replace('expected input version 3.5 to 3.7', 'expected input version 3.5 to 4.0')
anchor = '    destination = runner_dir / template.name'
assert text.count(anchor) == 1
text = text.replace(anchor, '    text = adapt40(case, text, template, runner_dir)\n'+anchor)
exec(compile(text, str(previous), 'exec'), {'__file__': str(HERE / 'replay.py'), '__name__': '__main__', 'adapt40': adapt})
