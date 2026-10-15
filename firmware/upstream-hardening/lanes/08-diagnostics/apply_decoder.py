"""Apply decoder extension to a caller-owned repository staging copy, not live files.

Root separately publishes diagnostic-registry.json once 3.3 is frozen. Schema:
{"format":"EA9 diagnostic candidate pins v1","versions":{"3.3.0":{
"imageSHA256":"<full-image pin>","manifestSHA256":"<published manifest pin>",
"immutablePrefixSHA256":"<SHA256 pristine image bytes [0,0x4c00)>"}}}
All three pins are required; no placeholders/default/manifest-only trust fallback.
Never call this as part of installation verification.
"""
from pathlib import Path
import shutil
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def apply(work: Path):
    work = Path(work).resolve()
    assert work != ROOT, 'Apply to a review staging copy; root integrates shared scripts.'
    path = work/'scripts/decode-startup-diagnostics.py'
    s = path.read_text()
    anchor = 'if __name__==\'__main__\':main()'
    integrated = "if __name__=='__main__':\n    from startup_diagnostic_registry import main as registry_main\n    registry_main(ROOT, decode_pages)"
    if anchor not in s:
        # A fresh staging copy may already contain root's reviewed integration.
        assert s.count(integrated) == 1, 'Unknown decoder entry point'
        target=work/'scripts/startup_diagnostic_registry.py'
        if target.exists():
            assert target.read_bytes() == (HERE/'decoder_extension.py').read_bytes()
        else:
            shutil.copyfile(HERE/'decoder_extension.py', target)
        return
    assert s.count(anchor) == 1
    s = s.replace(anchor, '''if __name__=='__main__':
    from startup_diagnostic_registry import main as registry_main
    registry_main(ROOT, decode_pages)''')
    path.write_text(s)
    shutil.copyfile(HERE/'decoder_extension.py', work/'scripts/startup_diagnostic_registry.py')
