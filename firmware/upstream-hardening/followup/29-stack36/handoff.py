"""Exact-image structural checks; no MCU/emulator execution or MMIO scheduling."""
import copy
import hashlib
import json
import re
import struct


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def instructions(body):
    out = {}
    for line in body.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4} )*[0-9a-f]{4})\s+([^\t]+)\t?(.*)', line)
        if m:
            out[int(m[1],16)] = (m[3].strip(), m[4].split('@')[0].strip(), len(m[2].replace(' ',''))//2)
    return out


def mask_inventory(bodies):
    return [dict(function=name,operation=op,operand=operand)
            for name,body in sorted(bodies.items())
            for _,(op,operand,_) in instructions(body).items()
            if op in ('cpsid','cpsie','msr','mrs')]


def verify_paths(insns):
    # The reviewed suffix is acyclic. Every conditional branch is explored;
    # calls return in this structural proof. No source-path feasibility assumed.
    paths=[]
    def walk(pc,trace,active):
        require(pc not in active and len(active)<100,'handoff suffix cycle')
        if pc == 0x5edc:
            paths.append(tuple(trace)); return
        require(pc in insns,'handoff leaves reviewed suffix')
        op,arg,size=insns[pc]
        nxt=pc+size
        if op=='bl':
            target=re.search(r'<([^>]+)>',arg)
            require(target is not None,'handoff unknown call')
            if target[1] in ('em_eic_init','on_cs_edge','em_uart_rx_reset','em_eic_start'):
                trace=trace+[target[1]]
        elif re.fullmatch(r'b(?:[a-z]{2})?(?:\.[nw])?',op):
            dest=int(arg.split()[0],16)
            walk(dest,trace,active|{pc})
            if op in ('b','b.n','b.w'):return
        require(op not in ('bx','blx','pop') and not arg.startswith('pc,'),'handoff unexpected return/indirect')
        walk(nxt,trace,active|{pc})
    walk(0x5ea0,[],set())
    expected={('em_eic_init','on_cs_edge','em_eic_start'),
              ('em_eic_init','em_uart_rx_reset','em_eic_start')}
    require(set(paths)==expected and len(paths)==3,'handoff ordering/path mismatch')
    return [list(p) for p in paths]


def verify_setup(insns,raw,symbols):
    expected={
        0x66de:('movs','r3, #128'),0x66e0:('movs','r4, #16'),
        0x66e2:('ldr','r2, [pc, #164]'),0x66e4:('str','r4, [r2, r3]'),
        0x66e6:('dsb','sy'),0x66ea:('isb','sy'),
        0x66ee:('ldr','r3, [pc, #156]'),0x66f0:('ldr','r2, [pc, #156]'),
        0x66f2:('str','r0, [r3, #0]'),0x66f4:('ldr','r3, [pc, #156]'),
        0x66f6:('str','r1, [r3, #0]'),
        0x67a8:('movs','r2, #16'),0x67aa:('ldr','r3, [pc, #4]'),
        0x67ac:('str','r2, [r3, #0]'),0x67ae:('bx','lr')}
    for pc,expect in expected.items():
        require(insns.get(pc,())[:2]==expect,'EIC disable/store/start instruction mismatch: '+hex(pc))
    word=lambda address:struct.unpack_from('<I',raw,address-0x5000)[0]
    require(word(0x6788)==word(0x67b0)==0xe000e100,'EIC NVIC base mismatch')
    require(word(0x678c)==symbols['g_cs_edge'] and word(0x6794)==symbols['g_vd_edge'], 'EIC callback storage mismatch')
    require(word(0x5f90)==symbols['on_cs_edge']|1 and word(0x5f88)==symbols['on_vd_edge']|1,'EIC callback registration mismatch')
    # ICER at base+0x80; value 16 selects bit 4 (IRQ4). ISER writes the same bit.
    return dict(disableStore='0x66e4',disableAddress='0xe000e180',irqMask='0x10',
                barriers=['0x66e6','0x66ea'],callbackStores=['0x66f2','0x66f6'],
                enableStore='0x67ac',enableAddress='0xe000e100')


def verify_vectors(raw,symbols):
    require(symbols['exception_table']==0x5000,'vector base mismatch')
    words=struct.unpack_from('<45I',raw)
    reserved={4,5,6,7,8,9,10,12,13,29,30,37,38,44}
    special={0:'_estack',1:'Reset_Handler',15:'SysTick_Handler',20:'EIC_Handler',26:'SERCOM1_Handler'}
    for index,word in enumerate(words):
        name=special.get(index,'Dummy_Handler')
        expect=0 if index in reserved else symbols[name]|(0 if index==0 else 1)
        require(word==expect,'vector target mismatch: '+str(index))
    return dict(wordsVerified=45,initialMSP=hex(words[0]),NVMCTRL='Dummy_Handler',
                reservedZeroSlots=sorted(reserved),specialSlots={str(k):v for k,v in special.items()})


def verify_callbacks(raw,symbols):
    word=lambda address:struct.unpack_from('<I',raw,address-0x5000)[0]
    for offset,name in [(48,'pump'),(52,'focus_retarget'),(56,'focus_abort')]:
        require(word(symbols['STOCK']+offset)==symbols[name]|1,'STOCK symbol binding mismatch')
    require(symbols['__preinit_array_start']==symbols['__preinit_array_end']==symbols['__init_array_start'], 'preinit symbol bounds mismatch')
    require(symbols['__init_array_end']-symbols['__init_array_start']==4 and word(symbols['__init_array_start'])==symbols['frame_dummy']|1,'init callback symbol binding mismatch')


def verify(bodies,raw,symbols,policy):
    require(mask_inventory(bodies)==policy['frozen35MaskInventory'],'global mask instruction inventory changed')
    for name,digest in policy['handoffBodySHA256'].items():
        require(hashlib.sha256(bodies[name].encode()).hexdigest()==digest,'handoff body mismatch: '+name)
    result={}
    result['paths']=verify_paths(instructions(bodies['em_init']))
    setup=instructions(bodies['em_eic_init']);setup.update(instructions(bodies['em_eic_start']))
    result['setup']=verify_setup(setup,raw,symbols)
    result['vectors']=verify_vectors(raw,symbols)
    verify_callbacks(raw,symbols)
    result['globalMaskInstructions']=mask_inventory(bodies)
    result['physicalIRQExecutionMeasured']=False
    result['model']='Static emitted instruction/control-flow review; no exceptions executed or scheduled.'
    return result


def guards(bodies,raw,symbols,policy):
    output=[]
    def reject(name,fn,diagnostic):
        try:fn()
        except ValueError as e:
            require(diagnostic in str(e),'wrong handoff negative-control failure: '+name+': '+str(e))
            output.append(dict(case=name,status='rejected',diagnostic=str(e)))
        else:raise ValueError('handoff guard accepted invalid evidence: '+name)
    path=instructions(bodies['em_init'])
    early=copy.deepcopy(path); early[0x5ec0]=('bls.n','5ed8 <em_init+0x168>',2)
    reject('branch-bypasses-rescue',lambda:verify_paths(early),'handoff ordering/path mismatch')
    missing=copy.deepcopy(path);missing[0x5ed8]=('nop','',4)
    reject('missing-deferred-start',lambda:verify_paths(missing),'handoff ordering/path mismatch')
    setup=instructions(bodies['em_eic_init']);setup.update(instructions(bodies['em_eic_start']))
    for name,address in [('missing-IRQ4-disable',0x66e4),('missing-disable-DSB',0x66e6),('missing-disable-ISB',0x66ea),('missing-IRQ4-enable',0x67ac)]:
        bad=copy.deepcopy(setup);bad[address]=('nop','',bad[address][2])
        reject(name,lambda:verify_setup(bad,raw,symbols),'EIC disable/store/start instruction mismatch')
    bad=bytearray(raw);struct.pack_into('<I',bad,21*4,symbols['EIC_Handler']|1)
    reject('NVM-vector-rebound',lambda:verify_vectors(bad,symbols),'vector target mismatch')
    badptr=bytearray(raw);struct.pack_into('<I',badptr,symbols['STOCK']+48-0x5000,symbols['focus_abort']|1)
    reject('STOCK-symbol-misbinding',lambda:verify_callbacks(badptr,symbols),'STOCK symbol binding mismatch')
    masked=copy.deepcopy(bodies);masked['em_eic_start']=masked['em_eic_start'].replace('67ae:\t4770      \tbx\tlr','67ae:\tb672      \tcpsid\ti')
    require(masked!=bodies,'mask control mutation missing')
    reject('new-global-mask',lambda:verify(masked,raw,symbols,policy),'global mask instruction inventory changed')
    return output
