"""AF3.9 failure-tail observed request counter; no protocol/control change."""
import hashlib
from pathlib import Path
if not __debug__:raise RuntimeError("Assertions required for source pin validation")
HOME_COMMAND_SHA256='5879886d57bf2114206f94626268a85b05b6afab4302bce80b60c06c1e285656'
MOTION_PINS={'motion_trace.c':'c0d76f011184f85ff1881463be8722b2d7cdb9aae911c016e270d7cc87d6fd90','motion_trace.h':'d3b28b9ff5e4c05fee7e0789c5062d7c848e475951af56c9615ddf814ca2155e'}
def apply(work):
    """Accept frozen AF3.8 home_command, allowing disjoint lane45 main edits."""
    work=Path(work)
    for name,digest in MOTION_PINS.items():
        assert hashlib.sha256((work/'src'/name).read_bytes()).hexdigest()==digest,name
    p=work/'src/main.c';s=p.read_text();start=s.index('static uint8_t home_command(void)\n{');end=s.index('\n}',start)+3
    old=s[start:end]
    assert hashlib.sha256(old.encode()).hexdigest()==HOME_COMMAND_SHA256,'home_command source pin'
    anchor='    g_next = c;\n';assert old.count(anchor)==1
    new=old.replace(anchor,'''    /* Count requests consumed after a recorded home fault, not motor starts. */
    uint8_t *home = (uint8_t *)(void *)(st_motion_data() + 112);
    if (motor_is_inhibited() && home[0] == 0x39 && home[3] != 255)
        ++home[3];
'''+anchor)
    p.write_text(s[:start]+new+s[end:])
