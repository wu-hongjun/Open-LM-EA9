# Astra 52: retained checkpoint and watchdog crash persistence

The AF 4.0 camera failure left all sixteen diagnostic pages erased. Existing
RAM traces flushed only at shutdown/fail-stop, so battery removal could discard
them. This lane adds observability and a crash latch; it does not change homing,
focus control or capture policy and does not identify the reported failure's
cause. Exact focus mode remains unknown.

The source-pinned applicator verifies six original source digests before making
changes to a private source copy. The frozen baseline manifest is
`8c55aaeed4cd15849907dae4457cadf6a070392141c95485041d40ddcdb85ffc`;
the AF 4.0 image is
`06385c36f0971f870bf9cfa402895d3e67310ed67ab2ca1578d1f0dfcf30aeae`.
The root integration owns target compilation, code margin, version 4.1,
decoder/host policy and release pins.

The retained object is 56 bytes: schema magic `0x31523945`, CRC32 over a 48-byte
existing summary, and that summary. It occupies a separate 64-byte NOLOAD SRAM
region at `0x20003fc0`; ordinary RAM allocation ends below this region. Startup
BSS clearing excludes it. Lane 53's original-bootloader model independently
checks retention against the modeled startup writes. This does not prove every
bootloader path or physical retention condition. CRC/schema validation remains
mandatory, and a WDT/system reset produces a cause-only record if RAM is invalid.

Each foreground checkpoint first invalidates its marker, copies the summary
under the existing IRQ lock, restores IRQ state, computes CRC and publishes its
marker last across compiler memory barriers. A reset during publication gives
an invalid checkpoint; a previous completed checkpoint is optional evidence.
Only the main thread calls this function. The ISR updates the live summary,
never the retained object. The checkpoint timestamp is a foreground sample time,
not a crash timestamp. No claim is made that all final events were captured.

The new type-5 page retains the v3 envelope and CRC. `n=1`, `chunk=0` means a
zero-filled baseline/cause-only payload; `chunk=1` means the retained 48-byte
summary. `reserved` is the raw reset cause. Only exact WDT (`32`) or system
(`64`) reset permits recovered RAM; mixed or cold/external causes reject it.
The boot page has its own append cohort. A later ordinary summary starts a new
cohort at its own slot. Retained magic is consumed before the write attempt.

The existing allocator advances beyond the highest occupied page, including
torn or foreign pages, never erases, and consumes a failed append without retry.
Full storage, read failure or write failure blocks the normal boot before motor
and protocol activation. A valid CRC-protected type-5 page with WDT/system bits,
matching physical slot/cohort and recognized basic layout latches crash state
across subsequent cold boots. The scanner is deliberately conservative: it can
latch a CRC-valid structurally matching crash record even if a stricter decoder
rejects additional payload semantics. It does not interpret retained payload to
decide whether motion may resume. Any nonerased page with invalid CRC also
latches the boot, as a storage-integrity failure rather than crash proof. This
includes torn writes that programmed some bytes. A completely erased interrupted
write is indistinguishable from unused space and cannot establish a latch.
Already-latched boots do not append again.

Target boot first executes the existing GPIO-only emergency motor release.
The WDT APBA bus mask is explicitly enabled. WDT ALWAYSON is rejected;
synchronization waits are finite. The WDT is disabled
before diagnostic programming, and current crash causes halt after recording.
Normal board initialization follows successful baseline persistence. This adds
boot NVM latency; no camera timing qualification has been performed.

Independent GCLK4 selects OSCULP32K, divided by 32. WDT uses 4096 cycles, nominally
four seconds subject to oscillator tolerance. Disabled preparation occurs before
protocol activation; arming occurs after protocol initialization and encoder
reference reads, with no synchronization wait while protocol is active. Service
requires 250 ms of progressing application time and a nonbusy WDT synchronizer.
It follows completed foreground main/servo work, never SysTick/IRQ activity or
an unbounded peripheral wait. Long legitimate servo retargeting can continue
servicing at completed iterations. Healthy idle also services it. A body-only
protocol deadlock while firmware keeps making these checkpoints is not detected.

The naked HardFault handler disables interrupts, executes a barrier, requests
AIRCR system reset, executes a barrier and loops. It does not trust SP or inspect
the exception frame. The subsequent record is labeled system reset, not a proven
HardFault. A hard fault before a checkpoint yields cause-only evidence. Existing
terminal fault/shutdown loops cease servicing WDT; a still-powered terminal
state may therefore reset into the same boot crash latch.

The actual watchdog C, with inert register definitions and no ARM assembly
execution, passed Clang ASan/UBSan tests for reset disposition, persistent latch,
ALWAYSON rejection, bounded stuck synchronization, disabled preparation,
asynchronous arm, 250 ms cadence, busy-clear suppression, frozen time and wrap.
Three deliberately broken controls failed: clearing while busy, clearing with a
frozen tick, and ignoring crash latch. Receipt:
`artifacts/private/astra52-watchdog-apba/result.json`. Lane 54 independently
tests retained CRC/publication, exact reset eligibility, interrupted/torn page
writes, exhausted tail and negative controls against the real trace C. Its frozen
receipt is `artifacts/private/astra54-powerloss-freeze/result.json`; 256 exact
reset causes, 448 retained bit flips, 512 flash bit flips, 65 torn write prefixes
and six failing mutation controls passed the intended acceptance assertions.

Remaining limits are explicit: power removed before reset/boot append can leave
only the baseline; WDT clock or reset hardware failure can prevent persistence;
bootloader diversion can prevent application logging; CRC is not cryptographic;
flash single-bank latency, physical motor state and real camera operation remain
unqualified. No hardware access, adapter inventory, app launch, canonical state
access or installation occurred in this lane.

## Host integration

The additive macOS/CLI integration names AF 4.1 `autofocusCrashDiagnostic`, uses
loader version `[4,1,0]`, and pins `ea9-af-crash-upstream.bin` through
`TrustedCrashUpstream` to SHA256
`fb59950b7d332a7f07749bda4d1604859b2361899ef220cb23bc10a383207641`.
The candidate manifest is
`557cceed31b13655b52bb786d1e2df80e6fb4016381f11c81d4dfe95a071fa6b`.
Historical resources, trust headers and command meanings remain unchanged.
The new explicit commands are `prepare-crash-upstream` and
`apply-crash-upstream`. The ordinary 4.0 installation hold remains in force.

App metadata is 0.24.0/build 33. The explicit install control labels 4.1 as
camera-unqualified, states the lack of a proven AF/crash fix, and retains the
fixed original lens restriction. Installed 4.1 selects USB tools rather than an
ordinary profile-change action. The behavior text distinguishes a startup
baseline from final-state evidence and explains the persistent crash latch.

All 53 named Swift tests passed (7 LensCore, 35 DeviceKit and 11 workflow tests),
including the new variant in full-image/profile-rejection and strict reconnect
verification tests. Workflow assertions check the continuing 4.0 hold, explicit
4.1 eligibility, USB consent, wrong-lens rejection, same-version reinstall guard,
and installed-4.1 tools behavior. Log:
`artifacts/private/astra52-host-swift-test.log`. No app or native CLI was launched;
packaging belongs to root integration. Candidate-bound watchdog tests also pass
at `artifacts/private/astra52-watchdog-candidate-final/result.json`, verifying all
manifest source pins and image hash before compiling the candidate's exact C.
