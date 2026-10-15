"""Apply the host-only proposal to a staged repository; never firmware files."""
from pathlib import Path
import shutil
import hashlib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def apply(root):
    root = Path(root).resolve()
    if root == ROOT:
        raise ValueError('Root owns shared integration; use a staged repository.')
    path = root/'scripts/startup_diagnostic_registry.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != 'e01c4b210577a22eec7cacd535a29ef31a272214247780e4432f7c958895ede8':
        raise ValueError('Host decoder differs from the audited frozen source.')
    text = path.read_text()
    old = '    return result\n\ndef main(root, decode_v1):'
    new = ('    from startup_diagnostic_cohorts import audit_cohorts\n'
           '    return audit_cohorts(data, result, version)\n\ndef main(root, decode_v1):')
    if text.count(old) != 1:
        raise ValueError('Expected one unchanged decoder return boundary.')
    path.write_text(text.replace(old, new))
    shutil.copyfile(HERE/'cohorts.py', root/'scripts/startup_diagnostic_cohorts.py')
    for relative in ('firmware/upstream-hardening/next/test_decoder.py',
                     'firmware/upstream-hardening/next35/test_decoder.py'):
        test = root/relative
        if not test.exists():
            continue
        before = "['decode-startup-diagnostics.py','startup_diagnostic_registry.py']"
        after = "['decode-startup-diagnostics.py','startup_diagnostic_registry.py','startup_diagnostic_cohorts.py']"
        text = test.read_text()
        if text.count(after) == 1 and before not in text:
            # Replay after root integration copies an already updated test list.
            continue
        if text.count(before) != 1:
            raise ValueError('Expected one staged decoder dependency list: '+relative)
        test.write_text(text.replace(before, after))
