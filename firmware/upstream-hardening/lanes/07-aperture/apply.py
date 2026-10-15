"""Bounded aperture grammar overlay after frame/TX/02/01 (03/05 optional)."""
from pathlib import Path
HERE = Path(__file__).resolve().parent

def apply(work: Path):
    work = Path(work).resolve()
    assert work != HERE.parents[3]/'firmware/upstream-diagnostic/build'
    p=work/'src/emount.c'; s=p.read_text()
    assert 'static const struct em_owned_request *g_retry;' in s
    def once(old,new):
        nonlocal s
        assert s.count(old)==1,(old,s.count(old))
        s=s.replace(old,new,1)
    once('\t\tem_m08_aperture_on = ((rx[7] & 0x80u) == 0u);\n\t\tem_set_aperture(g_aperture);','')
    once('\tframe = &ea9_data[p->offset];', '''	/* These handlers consume two payload bytes. A complete transport frame
	 * alone does not establish their operands: footer and window padding
	 * cannot supply them. This is a minimum, not a claimed full grammar. */
	if ((id == 0x08u || id == EM_ID_APERTURE || id == 0x34u)
	    && g_retry->length < 11u) return 1;
	/* Only an owned ordinary request commits negotiation. RX observation,
	 * overflow-rejected requests and raw capture echoes cannot alter it.
	 * A new session starts with the optional field absent. */
	if (id == EM_ID_SESSION || id == 0x08u) {
		em_m08_aperture_on = id == 0x08u && !(g_req[7] & 0x80u);
		em_set_aperture(g_aperture);
	}
	frame = &ea9_data[p->offset];''')
    once('there is nothing to obey; the reply echoes the requester\'s own bytes\n\t * back through the stored fixups.',
         'there is nothing to obey; the ordinary reply retains the fixed\n\t * nominal declaration instead of claiming physical movement.')
    once('The aperture is re-applied on the spot so the decision takes effect\n\t * without waiting for the next thing that happens to set it.',
         'This path records diagnostics only. The consumed ordinary request\n\t * commits the capability in em_send_id, outside receive interrupt context.')
    p.write_text(s)
    # Correct inherited claims without changing any lens or optical bytes.
    h=work/'src/emount.h';s=h.read_text()
    start=s.index('/* THE APERTURE this adapter declares')
    end=s.index('/* The current aperture, as 256 x AV + 4096',start)
    s=s[:start]+'''/* Fixed Contax 50 mm nominal f/1.4 declaration: native AV 0x1100,
 * legacy descriptor 0x10, equal electronic endpoints. The manual physical
 * iris is unknown: this is neither a sensor reading nor a wide-open claim.
 * Actual body metering and stopped-down AF require physical qualification. */
#define EM_APERTURE_MAX  0x1100u
#define EM_APERTURE_MIN  0x1100u
#define EM_APERTURE_NOW  0x1100u

'''+s[end:]
    start=s.index('/* d1 d0 d5 e8 e9 ef -- the pupil size')
    end=s.index('#define EM_SLOT_B_TYPE1',start)
    s=s[:start]+'''/* Inherited Sony SEL5518Z pupil-size curve, rescaled in the 3.1 baseline
 * builder from encoded 0x11c0 to 0x1100 by the f-number ratio. Preserved
 * unchanged here. This is not a measured Contax 50 mm optical calibration;
 * numerical consistency does not establish actual iris state or AF geometry. */
'''+s[end:]
    h.write_text(s)
