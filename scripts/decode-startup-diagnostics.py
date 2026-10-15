#!/usr/bin/env python3
"""Decode 3.2 application-tail records from a local native backup; no USB API."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT=Path(__file__).resolve().parents[1]
STAGES={1:'main',2:'clock',3:'tick',4:'encoder',5:'adc',6:'motor',7:'uart',
        8:'wait-cs-rise',9:'wait-cs-fall',10:'eic',11:'bus-ready',12:'reference',
        13:'loop',14:'connected'}
EVENTS={1:'stage',2:'cs-edge',3:'rx-frame',4:'tx-returned',5:'handshake',6:'fault',
        7:'first-window-preserved',8:'bad-rx',9:'shutdown-uart-disabled'}
FAULTS={1:'clock-wait',2:'encoder-wait',3:'adc-wait',4:'motor-wait',5:'uart-wait',
        6:'eic-wait',7:'tick-wait',8:'cs-rise-wait',9:'cs-fall-wait'}


def decode_pages(data):
    if len(data)!=1024:
        raise ValueError('Expected exactly 1024 diagnostic bytes.')
    pages=[]
    for index in range(16):
        p=data[index*64:(index+1)*64]
        if p==bytes([255])*64:
            pages.append({'slot':index,'state':'erased'});continue
        if (p[:4]!=b'E9S2' or p[4]!=1 or p[5] not in (1,2)
            or not 1<=p[6]<=16 or p[10:12]!=bytes(2)
            or int.from_bytes(p[8:10],'little')!=index
            or zlib.crc32(p[:60])!=int.from_bytes(p[60:64],'little')
            or (p[5]==1 and p[7]!=1) or (p[5]==2 and not 1<=p[7]<=4)):
            pages.append({'slot':index,'state':'invalid-or-torn'});continue
        q=p[12:60]
        entry={'slot':index,'state':'valid','boot':p[6],
               'type':'summary' if p[5]==1 else 'events'}
        if p[5]==1:
            entry['summary']={
                'stage':STAGES.get(q[0],f'unknown-{q[0]}'),'handshakeFlag':bool(q[1]),
                'fault':FAULTS.get(int.from_bytes(q[2:4],'little'),'none-or-unknown'),
                'uptimeMS':int.from_bytes(q[4:8],'little'),
                'rxFrames':int.from_bytes(q[8:10],'little'),'txReturns':int.from_bytes(q[10:12],'little'),
                'uartBytes':int.from_bytes(q[12:16],'little'),
                'uartErrors':int.from_bytes(q[16:18],'little'),'uartStatus':int.from_bytes(q[18:20],'little'),
                'lastRxMS':int.from_bytes(q[20:24],'little'),
                'firstRxID':q[24],'lastRxID':q[25],'firstTxID':q[26],'lastTxID':q[27],
                'message08CapabilityByte':q[28] if q[32] else None,
                'pins':None if q[29]==255 else q[29],
                'droppedEvents':int.from_bytes(q[30:32],'little'),
            }
        else:
            entry['events']=[]
            for k in range(p[7]):
                ms,kind,identifier,cls,seq,length,operand=struct.unpack_from('<IBBBBHH',q,12*k)
                entry['events'].append({'uptimeMS':ms,'kind':EVENTS.get(kind,f'unknown-{kind}'),
                    'id':identifier,'class':cls,'sequence':seq,'windowBytes':length,'operand':operand})
        pages.append(entry)
    return {'format':'EA9 startup trace v1','range':'[0x9c00,0xa000)',
            'timeBasis':'Firmware SysTick milliseconds; pre-tick stages use zero, and flash/IRQ pauses can lose ticks.',
            'validPages':sum(p['state']=='valid' for p in pages),
            'invalidPages':sum(p['state']=='invalid-or-torn' for p in pages),
            'erasedPages':sum(p['state']=='erased' for p in pages),
            'storageFull':all(p['state']!='erased' for p in pages),'pages':pages}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path,help='Native .ea9backup directory or 128 KiB flash.bin')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();source=args.backup
    manifest=None
    if source.is_dir():
        if (source/'manifest.json').stat().st_size>65536:
            raise SystemExit('Native backup manifest is too large.')
        manifest=json.loads((source/'manifest.json').read_text())
        source=source/'flash.bin'
    if source.stat().st_size!=0x20000:
        raise SystemExit('Expected exactly 128 KiB in flash.bin.')
    data=source.read_bytes()
    if len(data)!=0x20000 or data[0x4000:0x4003]!=bytes([3,2,0]):
        raise SystemExit('Expected a complete 128 KiB flash read reporting 3.2.0.')
    template=ROOT/'firmware/candidates/3.2.0/contax-zeiss-50-f1-4.bin'
    descriptor=json.loads(template.with_suffix('.manifest.json').read_text())
    expected=template.read_bytes()
    if (hashlib.sha256(expected).hexdigest()!=descriptor['imageSHA256']
        or len(expected)!=20480 or data[0x5000:0x9c00]!=expected[:0x4c00]):
        raise SystemExit('Immutable diagnostic firmware prefix does not match the pinned candidate.')
    if manifest is not None:
        file=manifest['files']['flash.bin']
        if (manifest['flashReadPasses']!=2 or manifest['auxiliaryReadPasses']!=2
            or file['bytes']!=len(data) or file['sha256']!=hashlib.sha256(data).hexdigest()):
            raise SystemExit('Native flash backup manifest does not match.')
    result=decode_pages(data[0x9c00:0xa000])
    result.update({'immutableCodePrefixMatches':True,'firmwareVersion':'3.2.0',
                   'flashSHA256':hashlib.sha256(data).hexdigest(),
                   'backupFlashManifestMatched':manifest is not None,
                   'cameraAcceptanceProven':False,'hardwareReportsSent':0})
    encoded=json.dumps(result,indent=2)+'\n'
    if args.output:
        with args.output.open('x') as handle:handle.write(encoded)
    else:print(encoded,end='')


if __name__=='__main__':main()
