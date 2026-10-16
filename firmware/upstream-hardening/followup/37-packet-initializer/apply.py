"""Lossless sparse storage for the frozen packet initializer, restored before the reset-handler VTOR rewrite."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=ROOT/'firmware/candidates/3.6.0/contax-zeiss-50-f1-4.manifest.json'
def apply(work):
    work=Path(work).resolve()
    assert work.is_relative_to(ROOT/'artifacts/private')
    assert work != ROOT/'artifacts/private/handoff36-repeat', 'Frozen base is immutable'
    pins=json.loads(BASE.read_text())['sources'];src=work/'src'
    for name in ('emount_packets.c','emount_packets.h','startup_samd21.c'):
        assert hashlib.sha256((src/name).read_bytes()).hexdigest()==pins['src/'+name],name
    path=src/'emount_packets.c';text=path.read_text()
    match=re.search(r'uint8_t ea9_data\[EA9_DATA_LEN\] = \{(.*?)\n\};',text,re.S)
    assert match
    data=bytes(int(s,16) for s in re.findall(r'0x([0-9a-f]{2})',match[1]));assert len(data)==1272
    mask=bytearray((len(data)+7)//8);values=bytearray()
    for i,value in enumerate(data):
        if value:mask[i//8]|=1<<(i%8);values.append(value)
    assert len(mask)==159 and len(values)==374
    def array(name,b):
        lines=[', '.join('0x%02x'%n for n in b[i:i+16]) for i in range(0,len(b),16)]
        return 'static const uint8_t '+name+'[] = {\n    '+',\n    '.join(lines)+'\n};\n'
    replacement=('/* Lossless representation of the pinned upstream packet initializer.\n'
        ' * Reset restores every byte after BSS clear and before its VTOR rewrite. */\n'
        'uint8_t ea9_data[EA9_DATA_LEN];\n'+array('packet_presence',mask)+array('packet_values',values)+
        'void ea9_packets_init(void)\n{\n'
        '    unsigned source=0;\n'
        '    for (unsigned dest=0;dest<EA9_DATA_LEN;dest++) {\n'
        '        uint8_t value=0;\n'
        '        if (packet_presence[dest>>3] & (1u<<(dest&7))) value=packet_values[source++];\n'
        '        ea9_data[dest]=value;\n'
        '    }\n}\n')
    path.write_text(text[:match.start()]+replacement+text[match.end():])
    path=src/'emount_packets.h';header=path.read_text()
    end='#endif /* EMOUNT_PACKETS_H */'
    assert header.count(end)==1
    path.write_text(header.replace(end,'/* Called once by Reset_Handler after BSS clear, before main. */\nvoid ea9_packets_init(void);\n\n'+end))
    path=src/'startup_samd21.c';text=path.read_text();anchor='\t/* Set the vector table base address */'
    assert text.count(anchor)==1
    text=text.replace(anchor,'\t/* Restore the packet table before this handler rewrites VTOR.\n\t * Boot may already have selected app vectors; IRQ quiescence is inherited. */\n\textern void ea9_packets_init(void);\n\tea9_packets_init();\n\n'+anchor)
    path.write_text(text)
