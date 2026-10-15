"""Source-consistency checks for pinned startup trace formats; no device I/O.

A CRC is an integrity check, not authentication. These checks recognize writer
invariants and cannot establish provenance of arbitrary CRC-recomputed bytes.
"""


def audit_cohorts(data, result, version):
    pages = result['pages']
    expected_version = 1 if version == '3.2.0' else 2
    for entry in pages:
        if entry['state'] != 'valid':
            continue
        slot = entry['slot']
        p = data[slot*64:(slot+1)*64]
        issues = []
        entry['semanticIssues'] = issues
        if p[4] != expected_version:
            issues.append('record-version-does-not-match-pinned-writer')
        if entry['boot'] > slot+1:
            issues.append('boot-start-is-after-record-slot')
        if entry['type'] == 'summary':
            if p[13] > 1 or p[44] > 1:
                issues.append('nonboolean-summary-flag')
            reserved = 49 if p[4] == 2 else 45
            if any(p[reserved:60]):
                issues.append('nonzero-summary-reserved-bytes')
            if p[4] == 2:
                if entry['boot'] != slot+1:
                    issues.append('summary-not-at-cohort-start')
                buffered, planned = p[46:48]
                if planned != min(buffered, 4*(15-slot)):
                    issues.append('planned-events-disagree-with-slot-budget')
                dropped = int.from_bytes(p[42:44], 'little')
                omitted = buffered-planned
                if dropped < omitted or (buffered < 48 and dropped != omitted):
                    issues.append('dropped-events-disagree-with-retention-budget')
        else:
            if any(p[12+12*p[7]:60]):
                issues.append('nonzero-unused-event-bytes')
            if p[4] == 2:
                if entry['boot'] == slot+1:
                    issues.append('event-at-required-summary-slot')
                if slot-(entry['boot']-1) > 12:
                    issues.append('event-beyond-maximum-cohort-span')

    # Only v2 has one sealed, summary-first snapshot. v1 permits repeated
    # event/summary flushes and must not inherit v2 order or budget rules.
    for entry in pages:
        if entry.get('recordVersion') != 2 or entry.get('type') != 'summary':
            continue
        summary = entry['summary']
        start = entry['slot']
        if entry['semanticIssues']:
            # An inconsistent summary cannot impose a plan on surviving pages.
            summary.update(persistedEvents=0, eventSnapshotComplete=False,
                eventSnapshotStatus='inconsistent', eventSnapshotIssues=[])
            continue
        planned = summary['plannedEvents']
        expected_pages = (planned+3)//4
        surviving = 0
        surviving_events = []
        missing = False
        crossed_cohort = False
        cohort_issues = []
        for offset in range(1, expected_pages+1):
            slot = start+offset
            if slot >= len(pages):
                missing = True
                continue
            child = pages[slot]
            # A subsequent boot may legitimately reuse the slot of a zero-byte
            # failed write, or follow a torn page. Never count its events here.
            if (child.get('boot') != entry['boot'] or child.get('type') != 'events'
                    or child.get('recordVersion') != 2):
                missing = True
                if child.get('boot') is not None and child.get('boot') != entry['boot']:
                    crossed_cohort = True
                continue
            expected_count = min(4, planned-4*(offset-1))
            if len(child['events']) != expected_count:
                child['semanticIssues'].append('event-count-disagrees-with-summary-position')
            if crossed_cohort:
                child['semanticIssues'].append('same-cohort-events-after-other-cohort-page')
            if child['semanticIssues']:
                cohort_issues.append('inconsistent-event-page')
            else:
                surviving += len(child['events'])
                surviving_events.extend(child['events'])
        for child in pages:
            if (child.get('recordVersion') == 2 and child.get('type') == 'events'
                    and child.get('boot') == entry['boot']
                    and not start < child['slot'] <= start+expected_pages):
                child['semanticIssues'].append('event-page-outside-summary-plan')
                cohort_issues.append('event-page-outside-summary-plan')
        for kind, counter in (('rx-frame', 'rxFrames'), ('tx-returned', 'txReturns')):
            observed = sum(event['kind'] == kind for event in surviving_events)
            if observed > summary[counter]:
                entry['semanticIssues'].append('surviving-events-exceed-summary-'+counter)
        summary['persistedEvents'] = surviving
        summary['eventSnapshotComplete'] = (not entry['semanticIssues']
            and not cohort_issues and not missing and surviving == planned)
        summary['eventSnapshotStatus'] = ('inconsistent' if entry['semanticIssues'] or cohort_issues
            else 'complete' if summary['eventSnapshotComplete'] else 'partial')
        summary['eventSnapshotIssues'] = sorted(set(cohort_issues))

    for entry in pages:
        if entry['state'] != 'valid':
            continue
        if entry.get('recordVersion') == 2 and entry.get('type') == 'events':
            start = entry['boot']-1
            origin = pages[start]
            if (origin.get('type') != 'summary' or origin.get('recordVersion') != 2
                    or origin.get('boot') != entry['boot'] or origin.get('semanticIssues')):
                entry['associationIssues'] = ['missing-or-inconsistent-cohort-summary']
        entry['semanticIssues'] = sorted(set(entry['semanticIssues']))
        entry['recordTrust'] = ('inconsistent-with-writer' if entry['semanticIssues']
            else 'unassociated' if entry.get('associationIssues') else 'writer-consistent')
    result['semanticallyInconsistentPages'] = sum(bool(p.get('semanticIssues')) for p in pages)
    result['unassociatedPages'] = sum(bool(p.get('associationIssues')) for p in pages)
    result['recordTrustMeaning'] = ('Page state valid means structural/CRC validity only. '
        'writer-consistent means checked invariants of the pinned writer, not authentication, '
        'installation verification, physical execution or camera acceptance. '
        'Inconsistent pages are untrusted diagnostic bytes; unassociated event pages lack a usable summary. '
        'Partial snapshots retain only surviving evidence. No timestamp ordering is inferred across counter wrap.')
    result['installationVerificationPerformed'] = False
    result['cameraAcceptanceProven'] = False
    return result
