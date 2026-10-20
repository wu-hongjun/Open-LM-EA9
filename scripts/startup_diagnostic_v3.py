"""Offline, source-bound v3 targeted tracing. CRC validity is not provenance.

An intact summary describes a sealed RAM snapshot, not a completed shutdown.
Terminal pages are separate software breadcrumbs; missing pages prove nothing
about physical motion, power loss, the body or a shutter request.
"""
import struct
import zlib

FAULTS = {0: 'none', 1: 'clock-wait', 2: 'encoder-wait', 3: 'adc-wait',
    4: 'motor-wait', 5: 'uart-wait', 6: 'eic-wait', 7: 'tick-wait',
    8: 'cs-rise-wait', 9: 'cs-fall-wait', 10: 'uart-rx-drain-fault',
    11: 'home-failed', 12: 'motor-poll-budget', 13: 'servo-poll-budget',
    14: 'servo-runaway', 15: 'servo-wrong-way', 16: 'encoder-coordinate-capacity'}
EVENTS = {5: 'handshake', 6: 'fault', 7: 'first-window-preserved',
    8: 'bad-rx', 9: 'shutdown-uart-disabled', 11: 'owner-cs',
    12: 'owner-offer', 13: 'owner-take', 14: 'tx-start', 15: 'tx-return',
    16: 'shutdown-admit', 17: 'owner-complete', 18: 'owner-phase'}
FOOTERS = {1: 'VD-two-low', 2: 'VD-timeout', 3: 'PA23-write-reached',
    4: '100ms-tail-delay-returned', 5: 'terminal-st-fail'}
TYPES = {1: 'summary', 2: 'events', 3: 'motion', 4: 'terminal-footer'}
HOME_PHASE_FAULTS = {17: 'home-drive-unsettled', 18: 'home-settle-unsettled',
    19: 'home-poll-budget'}


def u16(p, offset):
    return int.from_bytes(p[offset:offset+2], 'little')


def u32(p, offset):
    return int.from_bytes(p[offset:offset+4], 'little')


def decode_pages(data, version='3.7.0'):
    if len(data) != 1024:
        raise ValueError('Expected exactly 1024 diagnostic bytes.')
    if version not in ('3.7.0', '3.8.0', '3.9.0'):
        raise ValueError('Unsupported targeted-trace version.')
    faults = {**FAULTS, **HOME_PHASE_FAULTS} if version in ('3.8.0', '3.9.0') else FAULTS
    maximum_fault = 19 if version in ('3.8.0', '3.9.0') else 16
    pages = []
    for slot in range(16):
        p = data[64*slot:64*(slot+1)]
        e = {'slot': slot, 'state': 'invalid-or-torn'}
        pages.append(e)
        if p == b'\xff'*64:
            e['state'] = 'erased'
            continue
        if (p[:4] != b'E9S3' or p[4] != 3 or p[5] not in TYPES
                or not 1 <= p[6] <= 16 or p[11] != 0 or u16(p, 8) != slot
                or zlib.crc32(p[:60]) != u32(p, 60)
                or (p[5] != 2 and p[7] != 1)
                or (p[5] == 2 and not 1 <= p[7] <= 4)
                or (p[5] in (1, 4) and p[10] != 0)
                or (p[5] == 2 and p[10] > 7)
                or (p[5] == 3 and p[10] > 2)):
            continue
        q = p[12:60]
        e.update(state='valid', recordVersion=3, boot=p[6],
            type=TYPES[p[5]], chunk=p[10], semanticIssues=[])
        issues = e['semanticIssues']
        if p[6] > slot+1:
            issues.append('cohort-start-after-record-slot')
        if p[5] == 1:
            summary = {
                'uptimeMS': u32(q, 0), 'uartBytes': u32(q, 4), 'lastRxMS': u32(q, 8),
                'rxFrames': u16(q, 12), 'txReturns': u16(q, 14),
                'uartErrors': u16(q, 16), 'uartStatus': u16(q, 18),
                'evictedEvents': u16(q, 20), 'filteredEvents': u16(q, 22),
                'stageID': q[24], 'handshakeFlag': bool(q[25]),
                'faultID': q[26], 'fault': faults.get(q[26], f'unknown-{q[26]}'),
                'pins': None if q[27] == 255 else q[27],
                'firstRxID': q[28], 'lastRxID': q[29],
                'firstTxID': q[30], 'lastTxID': q[31],
                'observedMessage08CapabilityByte': q[32] if q[33] else None,
                'shutdownUARTDisabledObserved': bool(q[34]),
                'retention': 'last-32-focused-events', 'bufferedEvents': q[35],
                'plannedEvents': q[36], 'plannedMotionChunks': q[37],
                'capacityOmittedEvents': q[35]-q[36],
            }
            e['summary'] = summary
            budget = max(0, 11-slot)
            motion = 3 if budget >= 3 else 0
            if q[25] > 1 or q[33] > 1 or q[34] > 1:
                issues.append('nonboolean-summary-flag')
            if any(q[38:]):
                issues.append('nonzero-summary-reserved')
            if p[6] != slot+1:
                issues.append('summary-not-at-cohort-start')
            if q[35] > 32 or q[36] > q[35]:
                issues.append('invalid-retention-count')
            if q[37] != motion or q[36] != min(q[35], 4*(budget-motion)):
                issues.append('snapshot-plan-disagrees-with-page-budget')
            if q[35] < 32 and u16(q, 20):
                issues.append('evictions-with-not-full-ring')
        elif p[5] == 2:
            e['events'] = []
            for index in range(p[7]):
                ms, kind, identifier, flags, seq, lo, hi = struct.unpack_from('<IBBBBHH', q, 12*index)
                event = {'uptimeMS': ms, 'kind': EVENTS.get(kind, f'unknown-{kind}'),
                    'kindID': kind, 'id': identifier, 'flags': flags, 'sequence': seq,
                    'lengthOrSessionLow': lo, 'operandOrSessionHigh': hi}
                if 11 <= kind <= 18:
                    event['session'] = lo | (hi << 16)
                if 11 <= kind <= 18:
                    event['captureFlags'] = {
                        'rawCapture': bool(flags & 1), 'shutdownActive': bool(flags & 4),
                        'ownerPhase': bool(flags & 8), 'activeSlot': (flags >> 4) & 1,
                        'pendingOwner': bool(flags & 32), 'statusEnabled': bool(flags & 64),
                    }
                    if kind == 17:
                        event['captureFlags'].update(sessionStillValid=bool(flags & 2),
                            sendReturnedSuccess=bool(flags & 128))
                    elif kind == 12:
                        event['captureFlags'].update(offerAccepted=bool(flags & 128))
                    elif kind == 16:
                        event['captureFlags'].update(shutdownAdmitted=bool(flags & 128))
                    else:
                        event['captureFlags'].update(controlContext=bool(flags & 2),
                            resultBit=bool(flags & 128))
                    event['sequenceMeaning'] = ('owning-request-sequence' if kind in (14, 15) and flags & 2
                        else 'transmitted-frame-sequence' if kind in (14, 15)
                        else 'no-frame-identity' if kind in (11, 18) else 'received-request-sequence')
                    event['captureFlagsMeaning'] = ('Kind-specific software observations only; owner-phase is a local boundary, '
                        'not an atomic current-owner snapshot. TX return is not camera acceptance.')
                if (kind in (11, 18) and not flags & 1) or (kind in (14, 15) and not flags & 6):
                    issues.append('event-violates-focused-retention-filter')
                if kind not in EVENTS:
                    issues.append('filtered-or-unknown-event-kind')
                e['events'].append(event)
            if any(q[12*p[7]:]):
                issues.append('nonzero-unused-event-bytes')
        elif p[5] == 3:
            # Decoded only as a complete associated 144-byte snapshot below.
            e['motionChunkHex'] = q.hex()
        else:
            e['footer'] = {'kindID': q[0], 'kind': FOOTERS.get(q[0], f'unknown-{q[0]}'),
                'value': q[1], 'faultID': q[2], 'fault': faults.get(q[2], f'unknown-{q[2]}'),
                'ordinal': q[3], 'uptimeMS': u32(q, 4)}
            if q[0] not in FOOTERS or not 1 <= q[3] <= 4 or any(q[8:]):
                issues.append('invalid-terminal-payload')
            if ((q[0] == 1 and q[1] != 2) or (q[0] == 2 and q[1] > 1)
                    or (q[0] in (3, 4) and q[1] != 0)
                    or (q[0] == 5 and (q[1] != q[2] or not 1 <= q[1] <= maximum_fault))):
                issues.append('terminal-value-disagrees-with-writer')

    # A torn/empty write may be followed by another boot at a later frontier.
    # Never count that boot's pages as survivors of this summary's plan.
    for origin in pages:
        if origin.get('type') != 'summary':
            continue
        s = origin['summary']
        start = origin['slot']
        cohort = origin['boot']
        motion_n, event_n = s['plannedMotionChunks'], s['plannedEvents']
        planned_end = start+1+motion_n+(event_n+3)//4
        attached = []
        outside_plan = False
        for child in pages:
            if child is origin or child.get('boot') != cohort:
                continue
            slot = child['slot']
            delta = slot-start-1
            expected_type = ('motion' if 0 <= delta < motion_n else
                'events' if motion_n <= delta < motion_n+(event_n+3)//4 else
                'terminal-footer' if slot >= planned_end else None)
            if child['type'] != expected_type or origin['semanticIssues']:
                child['semanticIssues'].append('page-outside-usable-summary-plan')
                outside_plan = True
                continue
            if child['type'] == 'motion' and child['chunk'] != delta:
                child['semanticIssues'].append('motion-chunk-disagrees-with-position')
            if child['type'] == 'events':
                index = delta-motion_n
                if child['chunk'] != index or len(child['events']) != min(4, event_n-4*index):
                    child['semanticIssues'].append('event-chunk-disagrees-with-plan')
            if child['type'] == 'terminal-footer':
                expected_ordinal = slot-planned_end+1
                if child['footer']['ordinal'] != expected_ordinal:
                    child['semanticIssues'].append('terminal-ordinal-disagrees-with-position')
            attached.append(child)
        def intact(slot, kind):
            return (slot < 16 and pages[slot].get('type') == kind
                and pages[slot].get('boot') == cohort and not pages[slot]['semanticIssues'])
        if outside_plan:
            origin['semanticIssues'].append('cohort-has-page-outside-summary-plan')
        s['persistedEvents'] = sum(len(e.get('events', [])) for e in attached if not e['semanticIssues'])
        s['eventSnapshotComplete'] = (not origin['semanticIssues'] and all(
            intact(start+1+motion_n+i, 'events') for i in range((event_n+3)//4)))
        s['motionSnapshotComplete'] = (not origin['semanticIssues'] and motion_n == 3
            and all(intact(start+1+i, 'motion') for i in range(3)))
        if s['motionSnapshotComplete']:
            raw = b''.join(bytes.fromhex(pages[start+1+i]['motionChunkHex']) for i in range(3))
            s['motion'] = decode_motion(raw, version=version)
            if s['motion']['writerIssues']:
                origin['semanticIssues'].append('motion-payload-inconsistent-with-writer')
                s['motionSnapshotComplete'] = False
        s['snapshotStatus'] = ('inconsistent' if origin['semanticIssues'] else
            'complete' if s['eventSnapshotComplete'] and (motion_n == 0 or s['motionSnapshotComplete']) else 'partial')
        terminal = [e for e in attached if e['type'] == 'terminal-footer']
        previous = None
        expected_slot = planned_end
        chain_usable = s['snapshotStatus'] == 'complete'
        trusted_terminal = []
        for e in terminal:
            kind = e['footer']['kindID']
            if not chain_usable or e['slot'] != expected_slot:
                e.setdefault('associationIssues', []).append('missing-or-inconsistent-preceding-snapshot-or-footer')
                chain_usable = False
            if chain_usable:
                if (previous is None and kind not in (1, 2, 5)) or (previous is not None
                        and kind not in ({1: (3, 5), 2: (3, 5), 3: (4, 5), 4: (5,), 5: ()}.get(previous, ()))):
                    e['semanticIssues'].append('terminal-order-disagrees-with-writer')
                if e['semanticIssues']:
                    chain_usable = False
                else:
                    trusted_terminal.append(e['footer'])
                    previous = kind
                    expected_slot += 1
        s['terminalFooters'] = trusted_terminal
        s['terminalEvidenceMeaning'] = ('Software boundaries only. VD samples do not prove physical power removal; '
            'PA23-write-reached does not prove the pin voltage changed; tail-delay return does not prove camera shutdown. '
            'No footer, missing snapshot or absent event cannot prove success, no fault or no capture.')
    for e in pages:
        if e['state'] != 'valid':
            continue
        if e['type'] != 'summary':
            origin = pages[e['boot']-1]
            if (origin.get('type') != 'summary' or origin.get('boot') != e['boot']
                    or origin.get('semanticIssues')):
                e.setdefault('associationIssues', []).append('missing-or-inconsistent-cohort-summary')
        e['semanticIssues'] = sorted(set(e['semanticIssues']))
        e['recordTrust'] = ('inconsistent-with-writer' if e['semanticIssues'] else
            'unassociated' if e.get('associationIssues') else 'writer-consistent')
    frontier = max((e['slot']+1 for e in pages if e['state'] != 'erased'), default=0)
    return {'format': 'EA9 targeted trace v3', 'range': '[0x9c00,0xa000)',
        'validPages': sum(e['state'] == 'valid' for e in pages),
        'invalidPages': sum(e['state'] == 'invalid-or-torn' for e in pages),
        'erasedPages': sum(e['state'] == 'erased' for e in pages),
        'storageFull': all(e['state'] != 'erased' for e in pages),
        'appendFrontierSlot': frontier, 'appendablePages': 16-frontier,
        'appendExhausted': frontier == 16,
        'strandedErasedPages': sum(e['state'] == 'erased' and e['slot'] < frontier for e in pages),
        'semanticallyInconsistentPages': sum(bool(e.get('semanticIssues')) for e in pages),
        'unassociatedPages': sum(bool(e.get('associationIssues')) for e in pages),
        'bootMeaning': 'Append starting slot plus one; not a physical boot counter.',
        'timeBasis': 'SysTick milliseconds, unsigned wrap; flash/IRQ pauses can lose ticks. No cross-wrap ordering inferred.',
        'recordTrustMeaning': 'Structural/CRC validity and checked pinned-writer invariants are not authentication or proof of physical behavior.',
        'missingRecordsMeaning': 'Absent records prove no outcome. RAM loss, full storage, torn programming or interrupted flush can omit evidence.',
        'installationVerificationPerformed': False, 'cameraAcceptanceProven': False, 'pages': pages}


def decode_motion(raw, version='3.7.0'):
    """Decode the pinned main-context motion structure; no physical inference."""
    assert len(raw) == 144
    if version not in ('3.7.0', '3.8.0', '3.9.0'):
        raise ValueError('Unsupported motion-trace version.')
    if not any(raw):
        return {'valid': False, 'meaning': 'No servo move snapshot initialized; does not exclude motion outside this path.', 'writerIssues': []}
    if version == '3.9.0' and any(raw[112:]):
        return decode_failed_home(raw)
    i32 = lambda at: struct.unpack_from('<i', raw, at)[0]
    i16 = lambda at: struct.unpack_from('<h', raw, at)[0]
    direction = struct.unpack_from('<b', raw, 40)[0]
    count, next_slot = u16(raw, 44), raw[46]
    issues = []
    if (raw[0] != 1 or raw[1] != 1 or raw[2] > 1 or raw[3] > 1
            or direction not in (-1, 1) or raw[42] & ~7 or raw[43] > 5
            or next_slot > 3 or raw[54] > 6 or raw[55] or any(raw[112:])):
        issues.append('invalid-motion-layout-or-enum')
    if count < 65535 and next_slot != count % 4:
        issues.append('sample-cursor-disagrees-with-unsaturated-count')
    if raw[2] and (raw[43], raw[47]) not in ((3, 14), (4, 15)):
        issues.append('frozen-guard-outcome-disagrees-with-fault')
    if not raw[2] and (u32(raw, 24) or i32(28) or raw[47]):
        issues.append('guard-data-without-frozen-guard')
    samples = []
    for slot in range(4):
        at = 64+12*slot
        samples.append({'uptimeMS': u32(raw, at), 'position': i32(at+4),
            'requestedDuty': i16(at+8), 'stateFlags': raw[at+10], 'retargets': raw[at+11]})
    n = min(count, 4)
    ordered = [samples[(next_slot-n+i) % 4] for i in range(n)]
    if any(sample['stateFlags'] & ~7 for sample in ordered):
        issues.append('invalid-retained-sample-state-flags')
    if count < 4 and any(raw[64+12*count:112]):
        issues.append('nonzero-unused-sample-slots')
    if ordered and ordered[-1]['uptimeMS'] != u32(raw, 56):
        issues.append('last-ms-disagrees-with-newest-retained-sample')
    if raw[2] and (not ordered or ordered[-1]['position'] != i32(28)
            or ordered[-1]['uptimeMS'] != u32(raw, 24)):
        issues.append('guard-sample-does-not-match-last-retained-read')
    outcomes = {0: 'arrived', 1: 'stall', 2: 'timeout', 3: 'runaway', 4: 'wrong-way', 5: 'aborted'}
    completions = {0: 'none', 1: 'attempt', 2: 'queued', 3: 'suppressed',
        4: 'queue-full', 5: 'tx-return', 6: 'aborted'}
    return {'valid': bool(raw[1]), 'frozenFirstGuard': bool(raw[2]), 'dryRun': bool(raw[3] & 1),
        'beginMS': u32(raw, 4), 'initialStart': i32(8), 'initialTarget': i32(12),
        'target': i32(16), 'legStart': i32(20), 'guardMS': u32(raw, 24), 'guardPosition': i32(28),
        'requestedDuty': i16(32), 'commandOperand': u16(raw, 34), 'commandOp': raw[36],
        'acceptedOp': raw[37], 'acceptedOperand': u16(raw, 38),
        'direction': direction, 'retargets': raw[41], 'stateFlags': raw[42],
        'outcome': outcomes.get(raw[43], f'unknown-{raw[43]}'),
        'sampleCountSaturating': count, 'sampleNext': next_slot, 'samplesOldestFirst': ordered,
        'fault': FAULTS.get(raw[47], f'unknown-{raw[47]}'),
        'completionMS': u32(raw, 48), 'completionCode': raw[52], 'completionParameter': raw[53],
        'completionDisposition': completions.get(raw[54], f'unknown-{raw[54]}'),
        'lastSampleMS': u32(raw, 56), 'acceptedSampleMS': u32(raw, 60), 'writerIssues': issues,
        'meaning': 'Encoder coordinates and requested drive values from existing software reads; not physical displacement, polarity calibration, wire completion or optical focus.'}


def decode_failed_home(raw):
    """3.9-only reserved tail, written after inhibition; not a servo snapshot."""
    issues = []
    phase, flags, count = raw[113:116]
    if raw[112] != 0x39 or phase not in HOME_PHASE_FAULTS or flags & ~1:
        issues.append('invalid-failed-home-header')
    if (phase == 17 and flags & 1) or (phase == 18 and not flags & 1):
        issues.append('failed-home-phase-disagrees-with-drive-qualification')
    polls = u32(raw, 136)
    if (phase == 19 and polls != 1000000) or (phase in (17, 18) and polls >= 1000000):
        issues.append('failed-home-phase-disagrees-with-poll-budget')
    # The pinned foreground can enter servo only after successful homing, and
    # cannot home again afterward. A failed-home tail cannot coexist with it.
    if any(raw[:112]):
        issues.append('failed-home-tail-with-servo-data')
    signed = lambda at: struct.unpack_from('<i', raw, at)[0]
    start, end, threshold_ms, iteration = (u32(raw, at) for at in (116, 120, 132, 140))
    return {'valid': False, 'writerIssues': issues, 'homeDiagnostic': {
        'tag': raw[112], 'phaseID': phase,
        'phase': HOME_PHASE_FAULTS.get(phase, f'unknown-{phase}'),
        'driveQualified': bool(flags & 1),
        'consumedNonStopRequestsSaturating': count,
        'requestCountIsLowerBound': count == 255,
        'phaseStartMS': start, 'afterInhibitReleaseMS': end,
        'initialPosition': signed(124),
        'stillnessAnchorPosition': signed(128),
        'stillnessAnchorMS': threshold_ms,
        'sharedPollCount': polls,
        'lastEnteredIterationStartMS': iteration,
        'phaseElapsedTicksModulo32': (end-start) & 0xffffffff,
        'lastIterationToCutoffTicksModulo32': (end-iteration) & 0xffffffff,
        'meaning': ('Existing homing observations, sealed after motor inhibition. '
            'The stillness anchor is the initial or last threshold-crossing observation, '
            'not a final encoder read; positions are software coordinates. '
            'The last iteration interval includes pump and checks, not UART alone. '
            'Ticks can wrap or be lost; no physical duration or displacement is established. '
            'Count covers consumed non-Stop requests while inhibited after this tagged fault, '
            'not arrivals, retries, motor executions or camera shutter attempts; Stop is excluded. '
            'Zero does not exclude earlier, unconsumed or unpersisted requests. '
            'The record may span protocol sessions; it does not identify a shutter request.')},
        'meaning': 'No servo snapshot initialized; failed-home observations do not establish the physical fault or camera acceptance.'}
