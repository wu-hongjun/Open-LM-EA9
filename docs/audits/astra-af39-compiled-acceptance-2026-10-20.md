# AF3.9 compiled acceptance — conditional software bound

The frozen AF3.9 image and its independently rebuilt copy pass the image-bound
compiled audit. The conditional all-vector stack bound is **1,532 bytes** within
the 8,192-byte linker reserve. Code/data end is39,304 (`0x9988`), leaving632 bytes
before the unchanged16-page diagnostic region; static RAM is3,040 bytes.
Physical stack high-water, motor timing, camera acceptance and the physical
cause of AF3.8 fault17 remain unverified.

## Identity and composition

- Image SHA-256: `87b84a835ad6fed1437a975ca422fadec829fc3596425cd68cc570b6fb03fa44`.
- Manifest SHA-256: `9aa8b48b272db6709f281ecd91caceb675d07d79bba92d445e0e14112ca8c61a`.
- Reviewed policy SHA-256: `701af71a2b1733363a1c982ce6b9bd4b85af4489ea90ebb416a56ef254c40cf6`.
- Audit runner SHA-256: `56ab7f5c5607ab54d42aea9c805bbda825f25657cd654de07a2cd9d946223587`.
- Reproduction contract SHA-256: `035a6132b32458933ee4b360ac0f20ca9fd7b2a9d115efded1885fd363262583`.

The [receipt](../../firmware/upstream-hardening/next39/compiled-results.json)
records both private result hashes, full root chains, callback and NVM checks,
normalized-output pins, and rejection controls. Inputs are
`artifacts/private/homing39a` and `artifacts/private/homing39-repeat`.
The latter's image, raw bytes and manifest equal the reviewed first build.
Only ELF/map container hashes differ. Exact normalized objdump `-d`, `-t` and
`-p` output must match before those two hashes can be rebound; only the input
ELF pathname in the header is replaced. No instruction, symbol, address,
section or program-header difference is normalized away. A supplied policy
may alter only those two container hashes.

All49 source files match the final manifest. Reapplying the pinned lane45,
lane46 and lane48 transforms to the exact AF3.8 sources, then changing only
the version header, reproduces every final source byte. Only `main.c` and
`emount.h` differ from AF3.8. Lane47's optional arithmetic optimization is not
included. ELF load segments equal the raw image, the published-format prefix
equals those bytes, and all remaining image bytes—including the whole
`[0x9c00,0xa000)` diagnostic window—are erased padding.

## Analyzer scope and stack result

The frozen3.7 graph analyzer remains hash-bound. A private, hash-bound adapter
changes exactly its two static-RAM constants from3044 to3040: the validation
constant and the returned field. Graph construction, unknown-edge/frame
rejection, recursion rejection, source/manifest/compiler-stack binding,
exception accounting and stack reserve checks remain unchanged. The adapter
is generated in a private temporary directory and never overwrites old audits.
The old semantic-check module and baseline3.8 ELF are separately pinned.

The audit covers148 emitted functions,504 call sites and12 indirect sites with
no unresolved edges, unbounded frames or recursive components. Compiler `.su`
records match the pinned manifest; all library stack instructions match the
previous reviewed operations. Main's frame grows from88 to104 bytes, accounting
for the16-byte increase from AF3.8's1,516-byte bound. The foreground reset chain
is1,116 bytes; EIC is168, UART32, SysTick0 and Dummy0. The conservative model
charges36 bytes per exception including alignment, all three active application
handlers, a fourth configurable-priority dummy level, HardFault and NMI:
1,116 +168 +32 +6×36 =1,532 bytes. Tail branches retain full additional callee
frames. The more restrictive default-priority bound is1,388 bytes.

The model requires valid ARMv6-M control flow, intact callback/configuration
memory, ordinary privileged MSP thread entry and the recorded startup
assumptions. Inherited boot IRQ/priority/pending/active state, asynchronous
vector-transition delivery, failed stacking and memory corruption remain
outside this conditional guarantee. No stack canary/high-water, ISR duration
or NVM timing measurement was made.

## Callback, memory and wait review

The first ten indirect-call PCs remain unchanged. The two libc sites move to
`0x95cc` and `0x95d6`: preinit is empty at`0x9970`; the one init-array entry
at`[0x9970,0x9974)` is `frame_dummy|1`. Clone endpoint literals equal
`__TMC_END__` (`0x9984`) and both weak targets remain zero. Main's literal
registrations at`0x86d0`/`0x86d4` still target `powerdown_signal` and
`motion_shutdown_inhibit`. Compiled STOCK pointers, EIC callback storage,
registration instructions, priority setup, handoff paths and all45 vector
words are checked. No opaque callback context was added.

Shutdown, emergency fail-stop, UART disable and bounded delay operations match
AF3.8. Eight occurrences of shifted RAM literals are explicitly resolved to
the same named variables: receive bytes/errors/status, UART disabled state and
millis. Numeric literal values are otherwise preserved. This reviewed
cross-version comparison is separate from repeat-build normalization, which
permits only the ELF header pathname to change.

The emitted failed-home record follows `motor_inhibit` at`0x852a`; the collector
base is aligned, stores occupy only existing bytes112–143 and the tag store
at`0x8566` is last. The only new timestamp is after inhibition. The extra
suppression count increments only the tagged tail byte115 and saturates at255;
Stop branches around it. These are RAM writes, with no new peripheral or flash
access. Existing loop and cancellation behavior remains subject to the
separate source-bound homing fixtures.

No release ADC conversion/init/tracking symbol remains linked. This removes
the unused telemetry wait dependency; it does not demonstrate that an ADC wait
caused the observed physical failure. The remaining bounded-wait macro and
peripheral source files are unchanged. Diagnostic NVM callers remain exactly:
`powerdown_signal`/`st_fail` → `st_flush`/`st_terminal` → `append` →
`st_write_page`; reads are from `append` and `st_init`. EIC, UART, SysTick,
ordinary trace recording and motion-completion descendants have no path to
NVM or fail-stop. Source checks retain UART-disable-before-flush, nested
PRIMASK restoration and shutdown inhibition before admission.

## Reproduction and controls

From the repository root, with a fresh private result path:

```sh
python3 firmware/upstream-hardening/next39/compiled_audit.py \
  --build artifacts/private/homing39-repeat \
  --output artifacts/private/compiled39-recheck.json
```

Both builds pass. Internal negative controls reject an unknown indirect site,
unknown library frame, recursive callback and wrong image pin. External controls
reject a supplied graph-policy change, a changed main instruction in a copied
ELF and Python optimization that disables assertions. Rejected runs create no
acceptance output. This receipt accepts only the stated offline software
properties; it grants no hardware, flash or camera-test authorization.

A supplementary read-only decoder review found the new failed-home invariants
consistent with this source: only successful homing sets `g_homed`, it is not
cleared afterward, and no later home attempt runs after success. Normal servo
initialization therefore cannot precede a failed-home tail in this build; its
first112 bytes must be zero. Fault17 has no drive qualification,18 has it, and19
may occur in either phase. Count255 is a saturation lower bound; the decoder
correctly distinguishes consumed non-Stop commands from arrivals, motor starts
or shutter events, and permits accumulation across protocol sessions.
