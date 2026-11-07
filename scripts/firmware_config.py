"""Offline configuration and source assembly; never imports a USB backend."""
import json
from pathlib import Path
import re
import shutil


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum, maximum):
    return type(value) is int and minimum <= value <= maximum


def load_config(path, releases):
    config = json.loads(path.read_text())
    require(isinstance(config, dict) and
            set(config) == {'schemaVersion', 'version', 'target', 'lens', 'reportedAperture'},
            'Unknown or missing configuration fields.')
    require(type(config['schemaVersion']) is int and config['schemaVersion'] == 1, 'Unsupported configuration schema.')
    version = config['version']
    require(isinstance(version, list) and len(version) == 3 and
            all(integer(v, 0, 255) for v in version), 'Version must contain three bytes.')
    require(not (releases / '.'.join(map(str, version))).exists(),
            'Published versions are immutable; choose a new version.')
    require(isinstance(config['target'], str) and
            re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', config['target']), 'Invalid target ID.')
    lens = config['lens']
    require(isinstance(lens, dict) and set(lens) == {'name', 'focalMM10', 'nominalMaximumFNumber'},
            'Unknown or missing lens fields.')
    name = lens['name']
    require(isinstance(name, str) and 1 <= len(name) <= 63 and
            all(32 <= ord(c) < 127 for c in name) and name == name.strip(),
            'Lens name must be 1–63 printable ASCII characters without outer whitespace.')
    require(integer(lens['focalMM10'], 10, 10000), 'Focal length must be 1–1000mm in tenths of a mm.')
    nominal = lens['nominalMaximumFNumber']
    require(type(nominal) in (int, float) and 0.7 <= nominal <= 64,
            'Nominal maximum f-number must be 0.7–64.')
    aperture = config['reportedAperture']
    require(isinstance(aperture, dict) and set(aperture) == {'maximumAV', 'minimumAV', 'initialAV'},
            'Unknown or missing reported-aperture fields.')
    # Descriptor and f-number tables in the inherited protocol cover this interval.
    require(all(integer(v, 4096, 7168) and v % 32 == 0 for v in aperture.values()),
            'Aperture AV values must be 4096–7168 in steps of 32.')
    require(aperture['maximumAV'] <= aperture['initialAV'] <= aperture['minimumAV'],
            'Initial aperture must be inside the reported range.')
    require(aperture['maximumAV'] <= 5632,
            'Largest-opening descriptor currently supports up to f/8 (AV 5632).')
    return config


def load_target(root, target_id):
    directory = root / 'firmware/targets' / target_id
    target = json.loads((directory / 'target.json').read_text())
    require(target['schemaVersion'] == 1 and target['id'] == target_id, 'Target identity mismatch.')
    start, size, limit = (target[k] for k in ('applicationStart', 'applicationBytes', 'codeAndDataLimit'))
    require(all(type(v) is int for v in (start, size, limit, target['ramEnd'])) and
            0 <= start < limit <= start + size and size <= 1024 * 1024, 'Invalid target memory layout.')
    for field in ('buildRules', 'includeDirectories'):
        require(isinstance(target[field], list) and target[field], 'Missing target build paths.')
        for name in target[field]:
            require(isinstance(name, str) and not Path(name).is_absolute() and
                    '..' not in Path(name).parts and not any(c.isspace() for c in name),
                    'Target build paths must be relative and contain no whitespace.')
    require(target['makefile'] in target['buildRules'], 'Target makefile is missing from build rules.')
    require(isinstance(target['elf'], str) and not Path(target['elf']).is_absolute() and
            '..' not in Path(target['elf']).parts, 'Target ELF path must be relative.')
    return directory, target


def source_files(root, target_directory):
    files = {}
    for directory in (root / 'firmware/core', target_directory / 'src'):
        for path in sorted(directory.iterdir()):
            if not path.is_file():
                continue
            require(path.name not in files, 'Duplicate core/target source: ' + path.name)
            files[path.name] = path
    return files


def assemble(files, destination):
    destination.mkdir()
    for name, path in files.items():
        shutil.copy2(path, destination / name)


def replace_once(text, pattern, replacement):
    result, count = re.subn(pattern, lambda _: replacement, text, flags=re.MULTILINE)
    require(count == 1, 'Configuration hook changed or missing: ' + pattern)
    return result


def apply_lens(config, directory):
    header = directory / 'emount.h'
    text = header.read_text()
    text = replace_once(text, r'^#define EM_FOCAL_MM10 \d+u$',
                        '#define EM_FOCAL_MM10 %du' % config['lens']['focalMM10'])
    for constant, field in [('MAX', 'maximumAV'), ('MIN', 'minimumAV'), ('NOW', 'initialAV')]:
        text = replace_once(text, rf'^#define EM_APERTURE_{constant}  0x[0-9a-fA-F]+u$',
                            '#define EM_APERTURE_%s  0x%04xu' % (constant, config['reportedAperture'][field]))
    header.write_text(text)
    # Frame 0x3f: header (6), status (1), name + NUL (64), checksum (2), tail (1).
    frame = bytes([0xf0, 74, 0, 2, 0, 0x3f, 0]) + config['lens']['name'].encode('ascii').ljust(64, b'\0') + bytes([0, 0, 0x55])
    require(len(frame) == 74, 'Lens-name frame overflow.')
    lines = ['\t' + ', '.join('0x%02x' % b for b in frame[i:i + 12]) + ',' for i in range(0, len(frame), 12)]
    packets = directory / 'emount_packets.c'
    text = replace_once(packets.read_text(), r'uint8_t em_msg_3F\[EA9_LEN_3F\] = \{[^}]*\};',
                        'uint8_t em_msg_3F[EA9_LEN_3F] = {\n' + '\n'.join(lines) + '\n};')
    packets.write_text(text)
