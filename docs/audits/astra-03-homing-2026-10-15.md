# Astra lane 03 — homing, cancellation and reference readiness

Offline proposal, October 15, 2026. No production source, release image or owner
Application Support file was changed. No device was enumerated/opened and no
USB/HID, flash, updater or motor operation occurred. Uploaded 3.2 remains neither
owner-reconnect-verified nor camera-tested by this work.

## Findings in frozen 3.2

1. `main.c:motor_home` pumps communication while driving but never consumes a
   Stop, checks shutdown, or checks session identity. Its later unconditional
   `abs_encoder_track_reset(); g_homed = 1` commits a reference after cancellation.
   The caller also unconditionally advances `step` to 1.
2. Both drive and settle timing caps fall through to the same successful origin
   reset. Continuous movement/noise until either cap is therefore reported ready.
   Encoder stillness and reaching a cap are distinct outcomes.
3. A frozen `millis()` makes either homing loop unbounded even when all supplied
   peripheral calls return. Existing peripheral polling budgets do not bound
   these outer loops.
4. Shutdown can arrive in the home `pump`: the park callback returns because
   `g_homed` is false, while the old home pulse remains active through shutdown
   processing. Homing later brakes/reattaches and declares readiness. Lane02's
   early shutdown latch and driver-level inhibition are necessary dependencies.
5. `park_to_infinity` has no shutdown/inhibition guard. If the driver is made
   safely inert, the old callback can still waste a complete servo timeout before
   acknowledgement. This overlay returns before encoder/servo/diagnostic work
   when shutdown or sticky inhibition is present.

Frozen main SHA-256:
`41022c2190421e2b96303428e621914ec8504d5e4d18dc54315109c623aeb009`.
Frozen released image SHA-256:
`e20f169d9476391a1b988da5122f534411ceecc6b282e7acb92b558256a7c0df`.
The runner verifies main against the committed 3.2 release manifest before use.

## Deliverable and integration contract

[`apply.py`](../../firmware/upstream-hardening/lanes/03-homing/apply.py) exports
`apply(work: pathlib.Path)`, where `work/src/main.c` is a disposable build copy.
It injects the two reviewed `.inc` files into main; there are no additional linked
C modules or headers. Apply after the framing, lane02 shutdown and lane01 capture
overlays. Source matches are asserted; old releases are never overwritten.

The resulting main keeps the existing drive direction, duty, noise band,
minimums, timing caps and mapping. It adds explicit untried/active/ready/cancelled/
failed states, success-only origin readiness, cancellation checks before drive,
before/after each pump and around origin reset, and a shared 1,000,000-iteration
fallback. `home_still_for` widens subtraction to avoid signed-overflow in its
local difference calculation. A failure inhibits motion until reset; cancellation
detaches immediately and permits a retry only on a fresh motion command. There
are at most two attempted homes per boot. A Stop clears queued motion and is
acknowledged; ordinary motion received while homing remains queued for success.
Capture completion alone does not grant a retry. The main loop advances its
ready step only when `g_homed` is true. Main-held `g_next` motion is tagged
with its session generation and rejected on execution after a session change.
`focus_exec` and query service also refuse work after shutdown/inhibition or
without handshake readiness. These final full-main guards are source-overlay
changes requiring the root composed test; the 44 extracted-function checks do
not execute the complete foreground loop. Physical origin is preserved on an
ordinary new session; capture exchanges do not cause rehoming.

Required integration APIs:

- Lane01 `em_session_generation()`: advances only for an admitted ordinary
  INIT/0x01 session opener, clears handshake readiness there, and does not advance
  for phase-driven capture closure or 0x0a.
- Lane02 `em_shutdown_requested()` and
  `em_set_shutdown_inhibit_handler(void (*)(void))`: publish shutdown before
  invoking the cutoff callback and before park/echo/delay work.
- Lane06 `motor_inhibit()`, `motor_is_inhibited()` and
  `motor_emergency_release()`: sticky reset-only inhibition, atomic guarded
  remux, and immediate GPIO-only cutoff with the existing pin convention.
  Cancellation uses transient release; failure/shutdown use sticky inhibition.

These dependencies are **mandatory integration gates**, not implemented or
electrically verified by this lane. The shutdown callback also latches volatile
`g_aborted`, preventing foreground motion admission. Actual driver tests must
prove an IRQ cannot inhibit and then have interrupted motor code remux afterward.
Root reported lane02 will remove the park invocation from shutdown entirely;
this lane's callback guard remains independent defense.

## Exact validation

Run from repository root with a fresh output directory:

```sh
python3 firmware/upstream-hardening/lanes/03-homing/test.py --output artifacts/private/astra-03-homing-v5
```

The completed run passed **44 checks** using Clang C11 `-O2 -Wall -Wextra
-Werror`, ASan and UBSan. The fixture compiles the exact extracted production
`motor_home`, `home_still` helpers and `park_to_infinity`; the overlay version also
executes its real added admission/cancellation helpers. Unused fixture-boundary
symbols are allowed because frozen and patched code have different dependencies.

Both frozen and overlay pass four controls: stationary feedback, travel followed
by stillness, millisecond wraparound, and a queued ordinary Move. Frozen 3.2
fails the same **18 intended negative controls** that the overlay passes:

- Stop before drive, during the initial voltage burst, during drive, during
  settle, and during origin reset.
- Shutdown before drive, during drive and during settle.
- New session during drive, during settle and during origin reset.
- Drive cap without stillness, settle cap without stillness, frozen clock.
- Explicit retry after cancellation and exhaustion of the two-attempt budget.
- Park callback while shutdown is pending and while driver inhibition is set.

The frozen-clock negative control uses a test-only longjmp after 1,000,010 pumps
to detect the frozen implementation's nontermination without an unbounded test.
The production overlay exits before that test escape. Tests also repeatedly
service cancelled/failed homes and verify no background retry; a third fresh
motion cannot restart a twice-cancelled home. Failure checks require no origin
reset and sticky motor inhibition. Cancellation at the origin-reset boundary
can already have changed the private tracker, but must leave readiness false.

Machine-readable results and input hashes are in
[`result.json`](../../firmware/upstream-hardening/lanes/03-homing/result.json).
The generated full overlay main hash in this run is
`790eee63b0d06a156c60d7f6d947ce7c60d2d9120f18f8a3830a2332f425de29`.

## Evidence boundaries and remaining risks

The harness supplies protocol admission, encoder trajectories, clock, voltage,
PWM/GPIO and NVM boundaries. It does not run the actual UART/IRQ dispatcher,
motor registers or physical plant. The iteration cap bounds software work only;
it is not a measured electrical pulse limit. The initial voltage-burst routine,
SPI waits and nested protocol service have their own time/peripheral behavior
outside this fixture. Composed lane01/02/06 tests and a fresh ARM link/footprint
measurement remain required. This lane makes no flash-fit claim.

There is a remaining instruction-level commit interval between the final
cancellation check and publishing `g_homed`: this fixture injects at callable
boundaries, not at every instruction. Driver inhibition protects shutdown drive,
but a composed review should decide whether session/Stop admission and reference
publication need a short critical section. The pre-existing focus mailbox
`em_take_focus_cmd` clears its pending bit before copying the volatile command;
this lane does not claim to repair that IRQ ownership race. Main-only polling
cannot guarantee an overwritten Stop will be observed. Generation tagging alone
also does not make the volatile protocol command copy atomic: a session IRQ
during command consumption needs protocol mailbox ownership protection, and
old protocol pending motion must be invalidated on ordinary session admission.
These are explicit root/lane01 composition gates.

Stationary feedback can mean a disconnected/frozen sensor or stiction away from
the endpoint. Passing these controls establishes a software reference policy,
**not physical infinity**. No new calibration, gains, motor polarity, stock
origin bytes or aperture assumptions are introduced. The October 12 factory
instruction evidence shows initialization followed by possible persistent
reference replacement and leaves normal homing-gate reachability unproved; it
does not justify transplanting that reference into this custom tracker.

The earlier `firmware/ea9/src/af_reference.*`, `af_readiness.h` and
`hosttest/test_home_readiness.c` informed the explicit states and retry bound;
their scheduler/controller was not transplanted. Other observations left open
include signed overflow after extremely long unwrapped tracking, half-turn
sampling aliasing, ordinary-servo timebase bounds, and communication after the
current fail-stop peripheral-fault path. Those need their own production-path
tests. No claim of stock equivalence or A7C II camera qualification follows.
