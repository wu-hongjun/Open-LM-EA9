#!/usr/bin/env python3
"""Mutate isolated Swift sources to prove production-path bank regressions fail.

No shared source changes, device enumeration, HID reports or canonical state.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); out=a.output.resolve()
    assert out.is_relative_to(ROOT/'artifacts/private'); out.mkdir(exist_ok=False)
    package=out/'isolated/apps/macos'; package.parent.mkdir(parents=True)
    shutil.copytree(ROOT/'apps/macos',package,ignore=shutil.ignore_patterns('.build','.swiftpm'))
    scripts=out/'isolated/scripts'; scripts.mkdir()
    shutil.copy2(ROOT/'scripts/swift-local.sh',scripts/'swift-local.sh')
    plan=package/'Sources/DeviceKit/BankPlan.swift'; original=plan.read_text()
    cases=[('erase-gap','bankInstallerMergesOpaqueGapSeedsSelectionAndPreservesRollbackMetadata',
        '        full.replaceSubrange(0x5000..<0xa000,with: bank.application)',
        '        full.replaceSubrange(0xa000..<0x10000,with: Data(repeating: 255,count: 0x6000))\n        full.replaceSubrange(0x5000..<0xa000,with: bank.application)'),
        ('page-after-start','metadataSwitchSendsOneReportVerifiesPendingAndCancelsWithoutReflash',
        '        // No cancellation query, CHECK, READ, END, retry or padding after START.',
        '        _ = try transport.send(.page(Data(repeating: 0,count: 64)))\n        // Deliberate failing control.'),
        ('ignore-protected-flash','strictVerificationRejectsEveryRegionTamperingAuxChangesAndSameConnection',
        'actual[0x4040..<0x20000] == expected[0x4040..<0x20000]', 'true')]
    results=[]
    for name,test,old,new in cases:
        assert original.count(old)==1
        plan.write_text(original.replace(old,new))
        log=out/(name+'.log')
        with log.open('w') as f:
            run=subprocess.run(['bash',str(scripts/'swift-local.sh'),'test','--filter',test],
                stdout=f,stderr=subprocess.STDOUT,timeout=240)
        text=log.read_text()
        assert run.returncode!=0 and 'Build failed' not in text and '✘ Test '+test in text,(name,text[-2000:])
        results.append(dict(control=name,test=test,rejected=True))
    plan.write_text(original)
    (out/'results.json').write_text(json.dumps(dict(hardwareAccess=False,controls=results),indent=2)+'\n')
    print('All three isolated Swift bank failing controls were rejected by their production-path tests.')


if __name__=='__main__': main()
