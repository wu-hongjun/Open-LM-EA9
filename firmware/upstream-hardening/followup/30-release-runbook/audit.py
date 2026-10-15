#!/usr/bin/env python3
"""Offline original evidence: read pinned Git text, write this lane's JSON.

Only read-only git show/ls-tree subprocesses are used. No imports of project
executable modules, networking, device APIs, application launch or canonical
state access. This is not a firmware test suite.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import re
import subprocess

LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[3]
source_pin = json.loads((LANE / 'source-pin.json').read_text())
original_commit = source_pin['originalSourceCommit']
assert re.fullmatch(r'[0-9a-f]{40}', original_commit)

def read_original(name):
    return subprocess.check_output(['git', 'show', f'{original_commit}:{name}'], cwd=ROOT)

spans = {
    'README.md': [(10, 23), (166, 179)],
    'firmware/README.md': [(1, 6), (40, 42), (75, 80), (102, 118)],
    'docs/macos-device-workflow.md': [(1, 20), (42, 64), (89, 108)],
    'docs/macos-prototype.md': [(1, 17), (151, 179)],
    'firmware/candidates/3.6.0/README.md': [(1, 6), (41, 54)],
    'docs/upstream-handoff-test.md': [(1, 94)],
    'firmware/upstream-hardening/next36/README.md': [(8, 24)],
    'apps/macos/Sources/DeviceKit/NativeHID.swift': [(127, 135)],
    'apps/macos/Sources/EA9CLI/main.swift': [(5, 15), (18, 41)],
    'apps/macos/Sources/OpenLMEA9/DeviceOverview.swift': [(237, 247)],
    'scripts/build-firmware.py': [(13, 16), (25, 35)],
    'scripts/build-upstream-baseline.py': [(10, 15), (51, 56)],
    'scripts/build-upstream-handoff.py': [(18, 36)],
    'scripts/test-upstream-handoff.py': [(10, 26)],
    'scripts/build-upstream-absolute.py': [(18, 36)],
    'scripts/build-upstream-bounded.py': [(18, 21)],
    'scripts/build-upstream-hardened.py': [(18, 21)],
}
source_bytes = {name: read_original(name) for name in spans}
text = {name: data.decode() for name, data in source_bytes.items()}
evidence = {}
for name, selections in spans.items():
    lines = text[name].splitlines()
    evidence[name] = {
        'sha256': hashlib.sha256(source_bytes[name]).hexdigest(),
        'excerpts': [{'start': first, 'end': min(last, len(lines)),
                      'text': '\n'.join(lines[first - 1:last])}
                     for first, last in selections],
    }
info_bytes = read_original('apps/macos/Info.plist')
info = plistlib.loads(info_bytes)
checks = {
    'firmware_index_calls_31_current': 'The current comparison is a [direct upstream 3.1 baseline]' in text['firmware/README.md'],
    'device_guide_calls_app_015_current': text['docs/macos-device-workflow.md'].startswith('# Device workflow: prototype 0.15.0, build 19'),
    'prototype_current_banner_014': '> Current app: **0.14.0, build 17**' in text['docs/macos-prototype.md'],
    'prototype_claims_state_flag_isolates_guard': '`--state-directory PATH` can isolate the persistent reconnect\nguard' in text['docs/macos-prototype.md'],
    'source_guard_is_canonical': 'safety = USBConnectionSafety(directory: USBConnectionSafety.canonicalDirectory)' in text['apps/macos/Sources/DeviceKit/NativeHID.swift'],
    'cli_explicit_handoff_variant': 'case "prepare-handoff-upstream", "apply-handoff-upstream": .autofocusStartupHandoff' in text['apps/macos/Sources/EA9CLI/main.swift'],
    'gui_has_36_install_action': 'Button("Install Upstream AF 3.6.0", action: model.installStartupHandoff)' in text['apps/macos/Sources/OpenLMEA9/DeviceOverview.swift'],
    'readme_legacy_build_block': 'python3 scripts/build-firmware.py\npython3 scripts/build-upstream-baseline.py' in text['README.md'],
    'readme_missing_handoff_builder': 'scripts/build-upstream-handoff.py' not in text['README.md'],
    'readme_missing_handoff_test_runner': 'scripts/test-upstream-handoff.py' not in text['README.md'],
    'handoff_source_base_35_exact_path': "BASE=ROOT/'artifacts/private/absolute35a'" in text['scripts/build-upstream-handoff.py'],
}
documents = [n for n in spans if n.endswith('.md')]
tracked_paths = set(subprocess.check_output(
    ['git', 'ls-tree', '-r', '--name-only', original_commit], cwd=ROOT, text=True).splitlines())
links = []
for name in documents:
    for match in re.finditer(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', text[name]):
        target = match.group(1).split('#')[0]
        if not target or re.match(r'[a-z]+://', target):
            continue
        resolved = (ROOT / name).parent.joinpath(target).resolve().relative_to(ROOT).as_posix()
        exists = resolved in tracked_paths or any(p.startswith(resolved + '/') for p in tracked_paths)
        links.append({'source': name, 'target': target, 'exists': exists})
result = {
    'scope': 'Static original-commit release/runbook documentation audit; no hardware or state access',
    'originalSourceCommit': original_commit,
    'sourcePinSHA256': hashlib.sha256((LANE / 'source-pin.json').read_bytes()).hexdigest(),
    'app': {'version': info['CFBundleShortVersionString'], 'build': info['CFBundleVersion'],
            'sourceSHA256': hashlib.sha256(info_bytes).hexdigest()},
    'observations': checks,
    'localMarkdownLinks': {'checked': len(links), 'missing': [x for x in links if not x['exists']]},
    'evidence': evidence,
}
output = LANE / 'result.json'
output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'output': str(output.relative_to(ROOT)), 'observations': checks,
                  'app': result['app'], 'localMarkdownLinks': result['localMarkdownLinks']}, indent=2))
