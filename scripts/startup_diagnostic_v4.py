"""4.1-only crash checkpoint extension of the pinned v3 wire format.

Record version remains 3. Firmware-version gating prevents earlier images from
admitting type5 records. This decoder never accesses hardware.
"""
from startup_diagnostic_v3 import decode_pages as _decode


def decode_pages(data, version='4.1.0'):
    if version != '4.1.0':
        raise ValueError('Unsupported crash diagnostic firmware version.')
    result = _decode(data, version=version)
    result['format'] = 'EA9 targeted trace v3 with 4.1 boot checkpoints'
    result['checkpointMeaning'] = ('Last validated foreground checkpoint; not exact crash registers or time. '
        'Immediate power loss before persistence, reset paths that do not reach the application, '
        'and a camera-only stall while foreground health continues can leave no crash checkpoint.')
    return result
