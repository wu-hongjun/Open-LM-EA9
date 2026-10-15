"""Apply verified frame admission to a fresh 3.2 source copy, never the release."""
from pathlib import Path
import shutil


def apply(work: Path):
    here=Path(__file__).resolve().parent
    src=work/'src'
    for name in ('em_frame.c','em_frame.h'):
        shutil.copyfile(here/'src'/name,src/name)
    path=src/'emount.c'; source=path.read_text()
    def replace(before,after):
        nonlocal source
        assert source.count(before)==1,before
        source=source.replace(before,after)
    replace('#include "startup_trace.h"','#include "startup_trace.h"\n#include "em_frame.h"')
    replace('\tif (n < EM_HEADER_LEN || rx[0] != EM_FRAME_START) {',
            '\tstruct em_frame_view view;\n\tif (em_frame_open(rx,n,&view) != EM_FRAME_OK) {')
    replace('g_req[i] = (i < n) ? rx[i] : 0;',
            'g_req[i] = (i < view.length) ? rx[i] : 0;')
    for before,after in [
        ('rx[5] == 0x08u && n >= 8','rx[5] == 0x08u && view.length >= 11'),
        ('rx[5] == EM_ID_APERTURE && n >= 11','rx[5] == EM_ID_APERTURE && view.length >= 11'),
        ('rx[5] == 0x04u && n >= 20','rx[5] == 0x04u && view.length >= 20'),
        ('rx[5] == 0x03u && n >= 16','rx[5] == 0x03u && view.length >= 16'),
        ('rx[5] == EM_ID_SESSION && n >= 17','rx[5] == EM_ID_SESSION && view.length >= 17'),
    ]: replace(before,after)
    path.write_text(source)
