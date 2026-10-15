# Astra follow-up 21 — archived query workload evidence

The locally archived public captures do **not establish a nonzero `0x22`/`0x2e`
query workload**. Fresh extraction of five Entropy512 recordings finds 840 body
`0x04` messages, all without records. Conservative parsing of the twelve
LexOptical text files finds 2,035 validated body `0x04` messages, with four Move
records and no queries. Consequently these archives cannot establish a maximum
query batch, query arrival rate, required answer latency, or adequacy of the
3.4 four-entry queues. No production change is proposed from this evidence.

Exact-source synthetic controls confirm the existing capacity policy: three or
four queries in one valid `0x04` are admitted but split across status frames;
a fifth pending query is not admitted. The test helpers' zero-filled state
header is unrealistic, but replacing it with the archived public A6000 state
pattern leaves these results unchanged. No demonstrated header/record-placement
bug was found in this lane.

## Public captures, parsed offline

[Analyzer](../../firmware/upstream-hardening/followup/21-workload/analyze.py) and
[aggregate results](../../firmware/upstream-hardening/followup/21-workload/capture-summary.json).
The analyzer reads only the named public archives and existing public extraction
script. It emits counts, hashes and timing aggregates; it publishes no frames.

| Entropy512 recording | Validated frames | Body 0x04 | Lens 0x06 | Median 0x04 interval, ms |
| --- | ---: | ---: | ---: | ---: |
| A6000 / EF50 / Viltrox | 834 | 205 | 201 | 16.6832 |
| A6000 / EF-S24 / Viltrox | 620 | 150 | 151 | 16.6840 |
| A6000 / SEL55210 / 210 mm | 724 | 176 | 177 | 16.6842 |
| A6000 / SEL55210 / 55 mm | 398 | 94 | 96 | 16.6827 |
| A6000 / SELP1650 | 880 | 215 | 216 | 16.6836 |
| **Total** | **3,456** | **840** | **841** | — |

Every listed body `0x04` is 22 bytes, leaving no records after its 13-byte state
header. Every listed lens `0x06` is 48 bytes, leaving no tail beyond its 39-byte
payload core. Thus this corpus contains **zero request/answer query pairs**.

The interval measurements use successive CS-start sample indices divided by the
recordings' 6 MHz sample rate. They describe ordinary message cadence in these
short initialization recordings, not query turnaround time. Recording durations
range from 2.628 to 5.107 seconds. Extraction retains the original limitations:
two undecodable early Viltrox windows, two partial windows and 22 complete windows
without a start edge. All 3,456 accepted frames pass UART framing, declared
length, checksum and terminator checks. The original `.sr` files remain unchanged.
This reruns the existing independent sampler, not the historical sigrok plugin.

The [public capture README](../../references/upstream/Entropy512/sigrok-dumps/lens_mounts/sony_emount/README)
identifies an A6000 and its capture setup; it supplies no A7C II workload.

| LexOptical text subset | Validated frames | Body 0x04 | Lens 0x06 |
| --- | ---: | ---: | ---: |
| fullinit + mainloop snippets | 16 | 2 | 1 |
| clocks-and-sync-lines, two files | 1,060 | 373 | 146 |
| partial init with clocks | 0 | 0 | 0 |
| Sony 28–70 mm | 451 | 109 | 106 |
| Sony 55 mm | 1,132 | 280 | 281 |
| Voigtlander, three files | 4,553 | 1,132 | 1,129 |
| Zeiss 28 mm, two files | 567 | 139 | 140 |
| **Total** | **7,779** | **2,035** | **1,803** |

Of those body messages, 2,031 have length 22; four have length 27 and contain
one five-byte `0x1d` Move record each. All 1,803 validated lens `0x06` messages
have length 48. None contains a query-answer tail.

This is a conservative recoverable subset. Each candidate is bounded by explicit
`Body->Lens`/`Lens->Body` markers. The parser removes bracketed clock annotations,
joins whitespace, then requires declared length, checksum and terminator. It
never joins across direction markers or guesses missing bytes. Seventeen
candidates fail validation. The partial-init file has 226 direction blocks but
no `F0` frame candidate; its clock/direction-only content supplies no payload
workload evidence. Directionless snippets are excluded. The
[author's README](../../references/upstream/LexOptical/E-Mount-Traffic-Samples/README.MD)
warns that logging interrupts messages. No LexOptical rate or response-time claim
is made, and zero accepted queries is not proof that rejected portions lacked them.

## What upstream research and factory findings add

The pinned [autofocus notes, §§2.3–2.5 and 4.2](../../references/upstream/weiziqian/E-mount-protocol-RE/docs/autofocus.md)
describe three-byte `0x22`/`0x2e` operand-conversion records and three-byte replies
in `0x06`. They describe answers from one request message arriving together in
the next status, expressly at **PROBABLE** confidence. The zero operand's special
meaning remains unknown. These are useful semantic hypotheses, not a published
query-burst trace or a measured deadline.

The archived [0x04 notes](../../references/upstream/weiziqian/E-mount-protocol-RE/docs/msg_0x04.md)
include stored a9 II/Yongnuo examples for Stop, Move and row-plus-Scan. Those
examples establish additional record shapes, but do not provide a query timing
series. The pinned upstream host tests create two-query record frames and post
synthetic answer queues; those are implementation tests, not camera captures.
The snapshot manifest is [sources.json](../../references/sources.json).

Read-only review of the pre-existing private REA archive confirms the narrower
factory observations already recorded in follow-up 16:

- `function-5308.json`, evidence
  `ev_fe024fd24d03a8e47565abd27ca72b9daffd5113202830a549917edeac5a84ae`,
  stages received instruction state and operands by frame shape.
- `function-5a2c.json`, evidence
  `ev_c560091e12e280d9c679e7541d6a0c32bf67a9c7a29d18cd35eb61907b6066f0`,
  stages completion events and changes the status length to 50.
- `function-8b70.json`, evidence
  `ev_407d75644b8bab5a2077d6cbc09e791989b74d8e9712c50ec40dde18e29d25ee`,
  runs the foreground loop through `0x5dd4` and `0x5e00`.

These selected decompiler records do not specify a four-entry query queue,
maximum camera query rate, or query deadline. They do not prove factory query
absence elsewhere. No factory bytes, disassembly, personal unit identifiers or
private camera frames are reproduced here. This lane did not rerun lane 04's
factory instruction/sequence campaign or lane 08's decoder campaign.

## Exact 3.4 capacity and helper realism

The [runner](../../firmware/upstream-hardening/followup/21-workload/run_batches.py)
verifies all 46 sources against the published
[3.4 manifest](../../firmware/candidates/3.4.0/contax-zeiss-50-f1-4.manifest.json)
before and after execution. The tested source is the existing private
`artifacts/private/bounded34b` composition, image SHA-256
`fe6e192162c51ca15836d8431d8c6846f7a95c034ec4d8dc7a2805f3eac2eab9`.

The source contract is:

- `emount.c:em_parse_records()` begins at frame offset 19, reads fixed-size
  three-byte queries, and admits them only while `g_query_n < EM_QUERY_Q` (4).
  A valid frame can contain more than four records; frame validation is not a
  promise that every query in it entered the queue.
- `main.c:focus_answer_queries()` converts at most four per call. Session,
  handshake, abort, shutdown and motor-inhibition checks constrain publication.
  `em_take_query()` retains pending requests when four answers already exist.
- `pump()` invokes that worker before `em_poll()`, outside `g_homed`. These are
  pure operand conversions; the homing position gate does not apply to them.
  Foreground service outside the pump has its own call sites; this test does
  not establish a CPU-time or interrupt-latency bound.
- `em_poll()` builds 48-byte idle status up to a 56-byte maximum. Eight available
  tail bytes carry two answers, also with a two-byte event, or one answer with
  a four-byte Drive event. Successful transmission removes only answers encoded
  in that status. Remainders wait.
- The 56-byte ceiling protects the following packet template in the stored
  table. It is an implementation storage boundary, **not a capture-derived
  universal E-mount maximum**. Increasing it alone would overwrite another
  template; changing it requires a separate storage and compatibility design.

The follow-up 16 helper creates a 25-byte message with one query, all-zero state
header, fixed synthetic sequence, and synthetic scheduling. The test controls
reuse its production-source worker/pump harness but add **multiple records in
one message**, with both that zero header and a state pattern taken from the
public A6000/Viltrox capture. This makes explicit the distinction between
syntactically admitted traffic and a real camera session. Both headers produce
identical admission and FIFO answers on exact 3.4.

[Results](../../firmware/upstream-hardening/followup/21-workload/batch-results.json):
28 cases pass under ASan/UBSan. Actual production protocol modules receive sealed
frames through the host CS/receive shim; actual production arithmetic calculates
the answers; encoded outgoing status lengths, checksums, terminators, tags,
values and FIFO order are checked. Synthetic I/O and readiness setup do not
constitute an end-to-end camera handshake or timing experiment.

| Synthetic input | Admitted | First status answers, idle / Drive | Eventually delivered |
| --- | ---: | ---: | ---: |
| One frame, 0 queries | 0 | 0 / 0 | 0 |
| One frame, 1 query | 1 | 1 / 1 | 1 |
| One frame, 2 queries | 2 | 2 / 1 | 2 |
| One frame, 3 queries | 3 | 2 / 1 | 3 |
| One frame, 4 queries | 4 | 2 / 1 | 4 |
| One frame, 5 queries | 4 | 2 / 1 | 4 |
| Eight cycles, 4 queries per cycle, idle statuses | 20 of 32 | 2 | 20 |
| Eight cycles, 4 queries per cycle, Drive every cycle | 14 of 32 | 1 | 14 |

A cycle here is one injected batch followed by one pump/status opportunity;
eight extra opportunities drain the remainder. It has **no claimed real-time
period**. The over-capacity tests expose existing non-admission, distinct from
losing an already-admitted answer. They do not establish that any camera sends
these loads. The three-query test concretely demonstrates the limit of the
upstream prose's “together in the next status” claim: the current source cannot
do that for three queries, or for two with a Drive event. Whether that matters to
a camera remains unmeasured. This is a compatibility evidence gap, not a newly
established 3.4 regression or a reason to invent a larger queue.

## Reproduction and decision

Use fresh private output paths:

```sh
python3 firmware/upstream-hardening/followup/21-workload/analyze.py \
  --output artifacts/private/astra21-public-recheck
python3 firmware/upstream-hardening/followup/21-workload/run_batches.py \
  --source artifacts/private/bounded34b \
  --output artifacts/private/astra21-batches-recheck
```

Retain the bounded 3.4 implementation and describe its limits accurately.
Future camera qualification needs observed request batch sizes, arrival versus
successful-status cadence, mixed event/query tails, and actual deferred-answer
behavior. Existing public idle cadence cannot substitute for these observations.
No arbitrary-load losslessness or next-status deadline claim is supported.

All work was offline: no network, hardware enumeration/open/report, flash,
updater, app launch or canonical application-state writes. Only lane-owned
scripts, aggregate evidence, this audit and fresh private scratch were written.
Root owns commits.
