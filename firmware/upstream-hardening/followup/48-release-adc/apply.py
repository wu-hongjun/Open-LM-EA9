"""Remove unused legacy ADC telemetry only when EA9_NO_LOG is selected."""
from pathlib import Path

def apply(work: Path):
    main=work/'src/main.c'
    text=main.read_text()
    declaration='\tuint16_t idle_lo, idle_hi, load_lo, load_hi;'
    assert text.count(declaration)==1
    text=text.replace(declaration,'\tuint16_t idle_lo, idle_hi;\n#ifndef EA9_NO_LOG\n\tuint16_t load_lo, load_hi;\n#endif')
    for original in ('\tvdd_track_sample();','\tvdd_track_reset();','\tvdd_track_result(&load_lo, &load_hi);',
                     '\tvdd_init();\n\tst_note(ST_STAGE,ST_ADC,0,0,0,0,millis());'):
        assert text.count(original)==1,original
        text=text.replace(original,'#ifndef EA9_NO_LOG\n'+original+'\n#endif')
    main.write_text(text)
