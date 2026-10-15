#!/usr/bin/env python3
"""Bind original findings to their pinned commit and inspect edited documentation.

Only repository file reads and read-only git rev-parse/show are used. No builds,
project-module imports, device APIs, network, app or canonical state access.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[3]
original = json.loads((LANE / 'result.json').read_text())
source_pin = json.loads((LANE / 'source-pin.json').read_text())
head = source_pin['originalSourceCommit']
assert re.fullmatch(r'[0-9a-f]{40}', head), 'Original source must be an exact commit'
current_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
sha = lambda data: hashlib.sha256(data).hexdigest()
before = {}
for path, evidence in original['evidence'].items():
    blob = subprocess.check_output(['git', 'show', f'{head}:{path}'], cwd=ROOT)
    before[path] = {'headSHA256': sha(blob), 'capturedSHA256': evidence['sha256'],
                    'matches': sha(blob) == evidence['sha256']}
docs = ['README.md', 'firmware/README.md', 'docs/macos-device-workflow.md',
        'docs/macos-prototype.md', 'docs/system-design-recommendation.md',
        'firmware/candidates/3.6.0/README.md', 'docs/upstream-handoff-test.md',
        'firmware/upstream-hardening/next36/README.md',
        'firmware/upstream-hardening/next35/README.md',
        'firmware/upstream-hardening/next/README.md',
        'firmware/upstream-hardening/README.md']
texts = {path: (ROOT / path).read_text() for path in docs}
readme, index, workflow, prototype = [texts[path] for path in docs[:4]]
checks = {
    'original_findings_bound_to_pinned_commit': all(row['matches'] for row in before.values()),
    'firmware_index_points_to_36': 'The latest candidate is [upstream AF 3.6]' in index,
    'firmware_index_old_source_is_scoped': 'Historical custom 3.0 build and checks' in index,
    'device_workflow_019_build23': '# Device workflow: prototype 0.19.0, build 23' in workflow,
    'prototype_019_build23': 'Current app: **0.19.0, build 23**' in prototype,
    'workflow_explicit_36_command': '`prepare-handoff-upstream` and `apply-handoff-upstream`' in workflow,
    'workflow_fixed_profile_scope': 'The upstream 3.1–3.6 candidates' in workflow and 'runtime profile row' in workflow,
    'prototype_fixed_profile_scope': 'Fixed upstream 3.1–3.6 images accept only the original unedited 50mm profile' in prototype,
    'false_guard_isolation_claim_removed': 'can isolate the persistent reconnect' not in prototype,
    'canonical_guard_lock_stated': 'reconnect guard and USB operation lock always remain in canonical' in prototype,
    'current_af30_milestone_label_removed': '[the current milestone](evidence/af-30-candidate-2026-10-13.md)' not in workflow,
    'readme_handoff_builder': 'python3 scripts/build-upstream-handoff.py --output ' in readme,
    'readme_handoff_test_runner': 'python3 scripts/test-upstream-handoff.py --build ' in readme,
    'readme_links_prerequisites': 'firmware/upstream-hardening/next36/README.md' in readme,
    'readme_no_app_launch_command': 'open "dist/Open LM-EA9.app"' not in readme,
}
links = []
for path, content in texts.items():
    for match in re.finditer(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', content):
        target = match.group(1).split('#')[0]
        if not target or re.match(r'[a-z]+://', target):
            continue
        links.append({'source': path, 'target': target,
                      'exists': (ROOT / path).parent.joinpath(target).exists()})
checks['local_markdown_targets_exist'] = all(row['exists'] for row in links)
result = {'scope': 'Pinned original commit vs current working-tree documentation only',
          'originalHEAD': head, 'currentHEAD': current_head,
          'sourcePinSHA256': sha((LANE / 'source-pin.json').read_bytes()),
          'before': before, 'afterChecks': checks,
          'after': {path: {'sha256': sha((ROOT / path).read_bytes()),
                           'text': content} for path, content in texts.items()},
          'localMarkdownLinks': {'checked': len(links),
                                 'missing': [row for row in links if not row['exists']]}}
(LANE / 'after-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'originalHEAD': head, 'currentHEAD': current_head, 'checks': checks,
                  'localMarkdownLinks': result['localMarkdownLinks']}, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
