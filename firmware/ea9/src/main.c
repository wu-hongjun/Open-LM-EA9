/* main.c -- the E-mount responder plus the closed-loop focus mechanism.
 *
 * This is the opt-in AF application, separate from metadata_main.c. The 2.4
 * build selects a stock-derived controller in factory_af/factory_servo; legacy
 * host tests retain the upstream servo. Bounded homing, command translation,
 * protocol service and session motion-fault ownership are shared policies.
 * Upstream camera measurements below belong to its a9 II, not our A7C II.
 *
 * REPLACES the open-loop version, which damaged nothing permanently but came
 * close.  That one drove a fixed duty for a fixed 200 ms with no feedback: at
 * 50% duty this mechanism covers more than its entire advertised travel in
 * that time, so every pulse ended against an end stop, and the 100% step
 * over-travelled hard enough that the stock firmware needed two power cycles
 * before it would drive the helicoid again.
 *
 * It answered its question -- the motor works, and a measurement run's two candidate
 * explanations were both wrong -- but the parameters were sized against a
 * result that had already been withdrawn, and it had no end-stop protection of
 * any kind.
 *
 * What this one does instead:
 *
 *   - CLOSED LOOP.  Every move has a target and stops there.  A timed pulse
 *     cannot do that; this is the single biggest change.
 *   - SMALL.  +-200 encoder counts = 50 protocol units = 3.4% of the
 *     advertised travel, against the previous version's 130%.
 *   - LOW DUTY, RAMPED.  Starts at 4% and climbs only while the mechanism is
 *     not moving, capped at 16%.  The mechanism never gets more force than it
 *     needed to start, and the duty at which it first moves is the measurement
 *     worth having.
 *   - RETURNS TO WHERE IT STARTED after every excursion, so the sequence is
 *     net-zero and cannot walk toward a stop.
 *   - STOPS THE WHOLE SEQUENCE on the first stall or runaway, instead of
 *     carrying on into the next step.
 *
 * This is still an experimental mechanism test. Guards depend on functioning
 * feedback, I/O and a time base; this fork has not been camera-qualified.
 */
#include "board.h"
#include "clock.h"
#include "delay.h"
#include "diag.h"
#include "em_eic.h"
#include "em_uart.h"
#include "emount.h"
#include "lens_profile.h"
#include "motor.h"
#include "abs_encoder.h"
#include "servo.h"
#ifdef EA9_FACTORY_AF
#include "factory_servo.h"
#define MOTION_PROFILE FACTORY_PROFILE
#else
#define MOTION_PROFILE UPSTREAM_PROFILE
#endif
#include "af_control.h"
#include "af_reference.h"
#include "af_completion.h"
#include "af_timing.h"
#include "io_guard.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
#include "trail.h"
#include "vdd.h"

#define MOTOR_PAGE0     28u
#define TRACE_PAGE0     24u
/* 25 is the gap between the homing trace (24) and the park traces (26, 27). */
#define FHIST_PAGE      25u

/* THE START-UP AND SHUT-DOWN PAGES ARE GONE.
 *
 * Sixteen of the thirty-two pages used to measure how a boot began and how a
 * session ended: two milestones, twelve one-second snapshots that dated the
 * body's two-second power cut, and two ticks measuring how long the adapter
 * stayed powered after the bus went quiet.
 *
 * All three questions are closed.  Start-up and shut-down are stable, the
 * snapshots have reported "ran past the cutoff" every run for many sessions,
 * and the quiet ticks were documented as doing nothing even when they were
 * added.  The boot TALLY stays -- it costs no pages, it is what selects the
 * slot, and it still says whether the body restarted us mid-session.
 *
 * The pages they held now go to the two measurements that are live: which
 * frame arrived in which transfer window, and more than five focus moves.
 */
#define QUIET_MS        100u        /* 12 missed frames: unambiguous */
/* ...but NOT the end of the session.  The body goes quiet for about that long
 * whenever its metering times out and comes straight back, so anything that
 * may only be written once waits for a silence no pause produces. */
#define NORM_QUIET_MS   2000u
#define QUIET_IDLOG_PAGE 3u

/* THE TRANSFER WINDOWS, one page per (length, id) kind the body sent.
 *
 * A frame is delimited by its chip select, but the number of bytes clocked
 * inside that window is not necessarily the frame's length -- and reading the
 * window as the frame drove the helicoid into its stop.  The
 * receiver already captures the first two windows of every kind, with the
 * declared length beside the byte count, and `trail_cap()` has existed to
 * write them out since the responder did.  Nothing ever called it.
 *
 * The session-wide list of distinct window sizes says 48, 16, 32 and
 * occasionally 23 or 27, but not WHICH frame arrived in which.  These pages
 * are that pairing. */
#define CAP_PAGE0       8u
#define CAP_PAGES       EM_CAP_SLOTS

/* The body's message 0x08 request, raw.  One page, taken back from the focus
 * list, because that frame arrives once per session and carries the bit that
 * decides whether message 0x28 reports the aperture. */
#define M08_PAGE        17u

/* NO TWO WRITERS MAY SHARE A PAGE.  A flash page cannot be rewritten between
 * erases, so a collision leaves the bitwise AND of both records -- readable,
 * plausible and wrong (NOTES.md 35).  The focus list draws on pages the
 * start-up and shut-down records used to own, so it is worth stating what is
 * left where:
 *
 *   0,1,2,4..7,16     focus moves 6..13   (were BOOT, INIT, IDLG, SNAP, QUIET)
 *   17                the body's message 0x08 request
 *   3                 the id log, at the first quiet
 *   8..15             the transfer-window captures
 *   18,19             build consistency and the build marker
 *   20..23, 29        focus moves 1..5
 *   24,26             encoder traces
 *   25                focus history
 *   27                the last focus moves
 *   28,30             the homing and park records
 *   31                the normal-class tally
 *
 * One page per focus move.  They must not overlap the homing record
 * (MOTOR_PAGE0) or the park records (MOTOR_PAGE0 + 2 + n): a flash page cannot
 * be rewritten between erases, so two writers sharing a page leave the bitwise
 * AND of both records, which is silent nonsense. */
static const uint8_t  FOCUS_PAGE[] = { 20, 21, 22, 23, 29,
                                       0, 1, 2, 4, 5, 6, 7, 16 };
#define FOCUS_PAGES (sizeof(FOCUS_PAGE) / sizeof(FOCUS_PAGE[0]))

/* The LAST few moves, written when the bus goes quiet.
 *
 * The five pages above cover the first five moves and then stop, which is the
 * wrong end of the session: focus5 ran for 61 s, made at least five moves, and
 * everything after move #4 -- including whatever happened when autofocus died
 * -- left no record at all.  A rolling record in RAM costs
 * nothing and covers the end.
 *
 * Page 27 was the SECOND park attempt's encoder trace.  A second park attempt
 * has never happened in any run. */
#define FOCUS_LAST_PAGE 27u
#define FOCUS_LAST_N    3u

/* The normal-class frame histogram: every (length, id) the body sent, with a
 * count.  trail_norm() has existed since the responder did and was never
 * called, so the one measurement that says WHICH command forms a body uses has
 * been collected in RAM and thrown away every run.
 *
 * This is page 31, which was the SECOND park attempt's MOTR record -- the
 * counterpart of the page 27 above, and unwritten for the same reason: no run
 * has ever parked twice.  A second park now leaves no MOTR page.  That is a
 * deliberate trade: the question on the table is which of the stock's four
 * inbound command lengths this body actually emits, and nothing else in the
 * trail answers it. */
#define NORM_PAGE       31u

/* The normal-class histogram, at most once.
 *
 * A flash page can be written once between erases, so the two callers -- the
 * park and the quiet detector -- must not both reach it.  A run that ends in a
 * power cut never parks, and a run that parks may never go quiet, so both are
 * needed and the guard is what makes having both safe. */
static uint8_t g_norm_written;

static void norm_page(void)
{
	if (g_norm_written) {
		return;
	}
	g_norm_written = 1;
	trail_norm(NORM_PAGE);
}

/* The quiet id log, at most once, for the same reason.
 *
 * It was written on EVERY quiet transition, and `quiet` clears again the
 * moment the body comes back -- so a session with several pauses wrote the
 * same flash page several times.  Flash bits only go 1 -> 0, so the page ends
 * up as the AND of every write: focus6 wrote 11 ids and later 20, and the
 * count decoded as 11 & 20 = 0, an empty page where two good ones had been. */
static uint8_t g_qidlog_written;

static void quiet_idlog_page(void)
{
	if (g_qidlog_written) {
		return;
	}
	g_qidlog_written = 1;
	trail_idlog(QUIET_IDLOG_PAGE);
}

/* Motor values and velocity-loop tuning below are inherited upstream policy.
 * REA recovers related factory constants, but not an ordinarily enabled homing
 * gate or this controller. See docs/af-reconciliation.md for the distinctions.
 * Upstream measurement comments describe its adapter, not this owner's unit. */
static void pump(int32_t pos);
static void focus_report_at(int32_t counts);
static uint8_t focus_feedback_valid(int32_t counts);
static uint8_t focus_retarget(int32_t *target);
static uint8_t focus_abort(void);
static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out);
static void    focus_exec(const struct em_focus_cmd *c);
static void    focus_answer_queries(void);
static void focus_hist_page(uint32_t page);
/* Where focus is heading, and how fast.  Feeds the two forward-looking fields
 * the stock leaves empty: message 0x06's one-frame-ahead position and message
 * 0x05's frames-remaining countdown. */
static struct focus_pred g_pred;
static void focus_report(void);
static void build_marker_page(uint32_t page);
static void trace_page(uint32_t page, unsigned k, const struct servo_result *r);

#define HOME_DUTY       800         /* 31.25%, stock 0x5e00 */

/* The recovered stock homing gate has no established ordinary enabling writer.
 * This candidate deliberately uses bounded post-handshake homing, not factory
 * persistence. af_reference.c owns its phase, direction and deadline policy. */
#define HOME_GATE_OPEN() 1

/* 800 = 31.25%: the stock's own homing duty.  It is the value the stock's own
 * (unreachable, servo.md 10) homing block uses, and this project's hardware
 * runs are what show that it moves this mechanism. */
#define PARK_DUTY       800

/* 1280 = 50% of PER, the stock's own limiter.
 *
 * RAISED TO 1664 (65%) AND PUT BACK.  The reason for raising it was sound --
 * some places along the travel report `duty_first` 1280, pinned against the
 * cap with the boost having nowhere to go, and those moves take a median of
 * 370 ms against 186 for the rest.
 *
 * But the cap is also what clamps the feedforward's first-step kick, which
 * for any move over 163 counts is asking for far more than the cap anyway
 * (2248 at 300 counts, 4009 at 2000).  So raising the ceiling raised the
 * opening kick on EVERY move, not only the stuck ones, and the camera run
 * that tried it came back slower across the board: median 402 ms against
 * 208, and seven of twenty-six moves cut short by the body.
 *
 * If it is worth trying again it should be as two ceilings -- the profile
 * clamped here and only the breakaway boost allowed past -- and on its own,
 * not alongside three other changes as it was in 5.03. */
#define MOVE_DUTY       1280

/* The speed range a Scan or a Drive is mapped into, in COUNTS PER SECOND.
 *
 * It used to be a duty range, because there was no velocity loop to give a
 * speed to and no measurement to convert one into.  There is now: the body's
 * magnitude maps onto a real speed and the loop delivers it, whatever duty
 * that takes.  Both fields still carry a speed in a unit the protocol does
 * not define (autofocus.md 3.3, 3.4), so the mapping is still a choice -- but
 * it is now a choice of speeds rather than of forces.
 *
 * The floor is about what duty 250 produces, i.e. just above the measured
 * breakaway band; below that no duty reliably moves anything. */
#define SCAN_V_MIN      4000
#define SCAN_V_MAX      40000

/* A scan must NOT slow down as it approaches the end of its window -- that is
 * the one thing a constant-speed sweep may not do -- but the profile slows
 * down near any target by construction.  Giving the scan a very short stop_ms
 * keeps v_target above v_cruise until the last hundred counts or so, which is
 * "constant speed, then stop" expressed in the same one law rather than as a
 * special case bolted beside it. */
#define SCAN_STOP_MS    8

#ifdef EA9_FACTORY_AF
/* Only wrapper limits/hooks are configurable here. Factory gains, speed
 * staircase, retained history and callback timeout live in factory_af.c. */
static const struct servo_cfg FACTORY_PROFILE = {
    .duty_max = MOVE_DUTY,
    .stall_ms = 300,
    .timeout_ms = 380,
    .total_ms = 5000,
    .pump = pump,
    .abort = focus_abort,
    .retarget = focus_retarget,
    .retarget_max = 16,
};
#else
/* Legacy upstream tuning uses 5 ms. Its measurements have not been repeated
 * on the owner's adapter. It is excluded from the new factory baseline. */
static const struct servo_cfg UPSTREAM_PROFILE = {
	/* Profile: v = remaining / 42 ms, the worst measured stopping distance
	 * per count/ms, so friction alone can always stop it. */
	.stop_ms   = 30,
	/* 25 counts/ms.  The stock's staircase tops out at 22.7 and the
	 * mechanism will do 61 at 65% duty, so this is deliberately near the
	 * stock's own working speed rather than near the hardware's limit --
	 * the first thing to raise if focus feels slow, and the easiest to
	 * raise safely because the profile bounds the approach regardless. */
	.v_cruise  = 25000,

	/* v = 0.0399 * (duty - 134) counts/ms, twenty points, both runs. */
	.ff_div    = 40,
	.ff_offset = 134,
	.tau_ms    = 26,          /* the DRIVEN time constant, not the coast */
	.kp_div    = 50,
	/* Arrival also requires the mechanism to be slow enough that the
	 * coast cannot carry it out of tolerance: 16 counts over a 33 ms
	 * coast is 0.5 counts/ms. */
	.v_arrive     = 500,
	.arrive_steps = 2,

	/* THE BREAKAWAY SEARCH: climb 2.5% of PER per 5 ms step while stuck,
	 * and drop the whole lot the instant the mechanism goes.
	 *
	 * The cost of too gentle a climb, measured on a camera: 13 of 36 moves
	 * needed a duty of 1200 or more to start, and those had a median of
	 * 370 ms against 186 for the rest.  At 12 per step the search from the
	 * feedforward's value up to 1200 takes 400 ms on its own.
	 *
	 * The climb rate has a broad optimum and both ends are worse --
	 * 12/cycle gives 189 ms and leaves stalls, 128/cycle gives 170, and
	 * anywhere from 40 to 100 gives 126-139.  64 is the middle of that
	 * plateau rather than its argmax, which is 80: a flat optimum should
	 * be taken at its centre, where being wrong about the mechanism costs
	 * least.
	 *
	 * boost_max has to let the total reach duty_max from a short move's
	 * small feedforward, so it is no longer 800. */
	.boost_up   = 12,
	.boost_down = 8,
	.boost_max  = 800,

	.duty_floor = 200,        /* below it, zero -- see servo.h */
	.duty_max   = MOVE_DUTY,

	.tolerance     = 12,
	.settle_counts = 40,
	.aim_ahead     = 0,       /* zero at this profile speed; see servo.h */
	.noise     = 8,
	.stall_ms  = 300,         /* must outlast the integral's climb */
	.timeout_ms = 3000,
	.total_ms   = 5000,
	.pump       = pump,

	/* Mid-move retargeting, as the stock does (EA9.md a measurement run).  retarget_min
	 * matches the 12-count retarget threshold so a repeated identical target is not
	 * a redirection. */
	.abort        = focus_abort,
	.retarget     = focus_retarget,
	.retarget_max = 16,
	.retarget_min = 12,

	/* Only a genuine slam goes through the brake: above 15 counts/ms the
	 * old way.  Unconditionally it cost 362 counts of extra overrun. */
	.reverse_brake_ms    = 20,
	.reverse_brake_above = 15000,
};
#endif

/* Set once homing has run.  Until then abs_encoder_track() is measured from
 * wherever the mechanism happened to be at boot, so zero is not infinity and
 * parking to it would drive somewhere arbitrary. */
static int      g_homed;

/* Which page the next park writes.  A flash page cannot be rewritten between
 * erases -- programming only clears bits -- so two parks writing the same page
 * leave the bitwise AND of both records, which is silent nonsense.  It happened:
 * boot 0 of the motor6 run reported duty_first = 0 alongside 2802 counts moved
 * in 60 ms, a speed never measured. */
#define PARK_ATTEMPTS 2
static unsigned g_park_n;
static uint32_t g_pa23_at;

static uint32_t g_boot;
static uint32_t g_flash_boots;
static struct ea9_af_state g_af_state;
static struct ea9_home g_reference;
static struct em_focus_cmd g_next;
static uint8_t g_next_pending;
static uint8_t g_powerdown_started;
static uint8_t g_abort_pending;

/* The build marker.  There is one configuration now, but the
 * page stays: an ASCII tag in the image is greppable before flashing and
 * self-identifying in a dump, and the whole point of it was that a bare
 * numeric flag is indistinguishable in a binary. */
static void build_marker_page(uint32_t page)
{
	uint32_t w[16];
	unsigned i;

	for (i = 0; i < 16; i++) {
		w[i] = 0;
	}
	w[0] = EM_DIAG_MAGIC;
	w[1] = EM_DIAG_FORMAT;
	w[2] = 0x30595244u;           /* "DRY0" -- coils live */
	w[3] = 0;
	w[4] = 3;
	w[5] = 0x46464F42u;           /* "BOFF" -- the full stock shutdown */
	diag_page(page, w, 16);
}

static void trace_page(uint32_t page, unsigned k, const struct servo_result *r)
{
	uint32_t w[16];
	unsigned i;

	for (i = 0; i < 16; i++) {
		w[i] = 0;
	}
	w[0] = EM_DIAG_MAGIC;
	w[1] = EM_DIAG_FORMAT;
	w[2] = 0x54524143u;           /* "TRAC" */
	w[3] = ((uint32_t)r->trace_n << 16) | (uint32_t)k;
	for (i = 0; i < r->trace_n && 4 + i / 2 < 16; i++) {
		w[4 + i / 2] |= (uint32_t)r->trace[i] << (16 * (i % 2));
	}
	diag_page(page, w, 16);
}

/* Everything the servo loop owes the rest of the system, once per iteration:
 * answer the body, and take a supply sample while the coils are live. */
static void pump(int32_t pos)
{
	/* Refresh the reported position BEFORE answering, not only between
	 * moves.
	 *
	 * The status pair goes out on every frame sync, about every 16 ms, and
	 * a move takes up to 185 ms -- so without this the body is told the
	 * pre-move position for roughly eleven consecutive frames while the
	 * mechanism is visibly moving.  A lens that reports a stale position
	 * during the only interval where it is changing is giving the body's
	 * focus loop nothing to work with.
	 *
	 * Guarded on g_homed: before homing, zero is not infinity, so the
	 * mapping has no anchor and the value would be meaningless. */
	if (g_homed && focus_feedback_valid(pos)) {
		/* Sample BEFORE reporting, so the forecast published this frame
		 * is built on the position published this frame and not on the
		 * previous one. */
		focus_pred_sample(&g_pred, pos, millis());
		focus_report_at(pos);
	}
	em_poll();
	vdd_track_sample();
}

/* Hardware adapter around the independently tested reference policy. */
static uint8_t io_stop_motion(void)
{
    if (!ea9_io_faults() && !g_af_state.shutdown) return 0;
    if (ea9_io_faults()) ea9_af_note_result(&g_af_state, SERVO_IO_FAULT);
    motor_emergency_release();
    ea9_af_end_motion(&g_af_state);
    return 1;
}

static uint8_t focus_feedback_valid(int32_t counts)
{
    if (counts < -120 || counts > FOCUS_TRAVEL_COUNTS + 120)
        ea9_io_trip(EA9_IO_ENCODER);
    return !io_stop_motion();
}

static void motor_home(void)
{
    uint16_t idle_lo, idle_hi;
    int32_t initial;
    if (io_stop_motion() || !ea9_af_begin_motion(&g_af_state)) return;
    vdd_read_burst(&idle_lo, &idle_hi, 20);
    initial = abs_encoder_track();
    if (io_stop_motion()) return;
    ea9_home_begin(&g_reference, initial, millis());
    vdd_track_reset();
    if (!MOTION_PROFILE.dry) {
        motor_attach_pins();
        motor_drive(-HOME_DUTY);
    }
    while (g_reference.phase == EA9_HOME_DRIVING || g_reference.phase == EA9_HOME_SETTLING) {
        enum ea9_home_phase previous = g_reference.phase;
        struct em_focus_cmd command;
        pump(0); /* no reference yet: publish no derived focus position */
        if (io_stop_motion()) { ea9_home_cancel(&g_reference); return; }
        if (em_take_focus_cmd(&command)) {
            if (command.op == EM_OP_STOP) {
                ea9_home_cancel(&g_reference);
                motor_release();
                ea9_af_end_motion(&g_af_state);
                g_next_pending = 0;
                em_post_event(EM_REC_STOP, 0x01u);
                return; /* unknown zero remains unknown until a new boot */
            }
            g_next = command; g_next_pending = 1; /* latest command waits for reference */
        }
        int32_t sample = abs_encoder_track();
        if (io_stop_motion()) { ea9_home_cancel(&g_reference); return; }
        ea9_home_sample(&g_reference, sample, millis());
        if (g_reference.phase == EA9_HOME_SETTLING && previous == EA9_HOME_DRIVING && !MOTION_PROFILE.dry) {
            motor_drive(0); motor_brake();
        }
    }
    if (g_reference.phase != EA9_HOME_READY) {
        ea9_af_note_result(&g_af_state, g_reference.outcome);
        motor_release(); ea9_af_end_motion(&g_af_state); return;
    }
    /* Commit only after both stages and a final fault-free encoder read. */
    abs_encoder_track_reset();
    if (io_stop_motion()) { g_reference.phase = EA9_HOME_FAILED; return; }
    g_homed = 1;
    ea9_af_end_motion(&g_af_state);
}

/* Park to infinity, called from the message 0x16 handler before the
 * acknowledgement goes out (emount.c).  The stock does the same thing with its
 * own stored park position.
 *
 * Bounded on purpose.  The body is waiting for the echo, so this gets one
 * attempt at a short timeout and whatever happens, happens -- emount.c sends
 * the acknowledgement regardless.  A lens left mid-travel is a much smaller
 * problem than a camera that will not switch off.
 *
 * Infinity is track position 0, where homing left the mechanism against the
 * stop.  Moving back to 0 stops `tolerance` counts short of the stop rather
 * than driving into it. */
/* The park keeps the stock homing duty.  It runs at shutdown, with the body
 * waiting on the acknowledgement, and it is not the thing under test. */
static const struct servo_cfg PARK = {
	.stop_ms    = 30,
	.v_cruise   = 25000,
	.ff_div     = 40,
	.ff_offset  = 134,
	.tau_ms     = 26,
	.kp_div     = 50,
	.v_arrive     = 900,      /* looser: the body is waiting */
	.arrive_steps = 2,
	.boost_up   = 12,
	.boost_down = 8,
	.boost_max  = 800,
	.duty_floor = 200,
	.duty_max   = PARK_DUTY,
	.tolerance     = 32,          /* looser than a move: near enough, and the
	                                body is waiting on the acknowledgement */
	.settle_counts = 80,
	.noise      = 8,
	.stall_ms   = 300,
	.timeout_ms = 1200,
	.pump       = pump,
	.abort      = focus_abort,
};

/* The tail of the stock shutdown (EA9.md a measurement run), after the acknowledgement.
 *
 * WHY PA23 IS NOW REPLICATED.  I left it out before as "unexplained", and the
 * shutdown still hung.  What is now known: the body does send message 0x16, we
 * do acknowledge it, we do park, and the body still keeps the adapter powered
 * for more than 4 s afterwards without saying anything.  It is waiting for
 * something, and PA23 is the only thing left in the stock sequence that a body
 * could possibly observe -- the other two steps (disabling our own UART, going
 * to sleep) are internal.
 *
 * atmel_start_init makes PA23 an output driven LOW and the stock drives it HIGH
 * here, which is the shape of a signal, not of a mode pin.  It doubles as the
 * bootloader's stay-in-bootloader input before the app configures it, which is
 * why it looked ambiguous; on the app side it is unambiguously an output.
 *
 * NOT reproduced: disabling the UART, and the halt.
 *
 * The UART disable was tried and reverted on the user's objection, which is a
 * good one: a lens that cannot hear anything cannot be woken, and the only way
 * back is a power cycle.  The behaviour it was meant to stop -- talking again
 * after announcing shutdown -- is better fixed in the protocol layer, where it
 * is reversible: after the acknowledgement the responder stays silent to
 * everything except a fresh session opener (emount.c).  Same observable
 * silence, no trap.
 */
static void powerdown_signal(void)
{
	uint32_t t0;
	int low = 0;

	if (g_powerdown_started) return;
	g_powerdown_started = 1;
	ea9_af_request_shutdown(&g_af_state);
	motor_inhibit();
	motor_release();
	diag_tally_mark(DIAG_MARK_SHUTREQ, 0);
	delay_ms(50);

	/* The stock's next step, in its order: switch the USART off before
	 * waiting for the frame sync and before PA23.
	 *
	 * Reverted once on the user's objection that a deaf lens cannot be
	 * woken, and proposed again by them now.  The objection is
	 * weaker than it was: the body is measured cutting power about 700 ms
	 * after PA23, so the deaf window ends in power loss.  em_uart_send()
	 * returns immediately once disabled -- it waits on DRE, which a
	 * disabled SERCOM never sets, so one send afterwards would hang the
	 * firmware for good.
	 *
	 * 2026-09-20: MEASURED, and it is load-bearing.  This step is the only
	 * difference between an image that boots normally and one that stalls
	 * on the next power-on -- a clean single-variable A/B on the a9 II.
	 * Do not remove it again without a measurement; it was dropped once
	 * on an argument and cost six hardware runs. */
	em_uart_disable();

	/* Wait for the frame sync to stop, as the stock does -- two consecutive
	 * low readings 1 ms apart -- but bounded, because a body that keeps
	 * clocking must not strand us here. */
	t0 = millis();
	while (!ea9_io_faults() && (uint32_t)(millis() - t0) < 500u) {
		delay_ms(1);
		low = em_pin_level(EM_PIN_BODY_VD) ? 0 : low + 1;
		if (low >= 2) {
			break;
		}
	}

	PORT->Group[0].OUTSET.reg = (1u << 23);
	g_pa23_at = millis();
	diag_tally_mark(DIAG_MARK_PA23, (uint8_t)low);
	delay_ms(100);
}

static void park_to_infinity(void)
{

	struct servo_result r;
	uint32_t w[16];
	int32_t  here;
	unsigned i;

	/* Shutdown can be received inside the current servo's protocol pump.
	 * Stop that owner rather than recursively starting another servo. */
	if (g_af_state.active || g_af_state.shutdown || ea9_af_faulted(&g_af_state)) {
		ea9_af_request_shutdown(&g_af_state);
		motor_inhibit();
		motor_release();
		return;                 /* a fault must not restart motion at shutdown */
	}
	if (!g_homed || g_park_n >= PARK_ATTEMPTS) {
		return;                  /* not homed, or out of pages to record in */
	}
	here = abs_encoder_track();
	if (here > -PARK.tolerance && here < PARK.tolerance) {
		return;                  /* already there */
	}

	if (!ea9_af_begin_motion(&g_af_state)) return;
	g_abort_pending = 0;
#ifdef EA9_FACTORY_AF
    factory_servo_move_to(0, &PARK, &r);
#else
	servo_move_rel(-here, &PARK, &r);
#endif
	ea9_af_end_motion(&g_af_state);
	if (ea9_af_note_result(&g_af_state, r.outcome) || g_af_state.shutdown) motor_release();

	for (i = 0; i < 16; i++) {
		w[i] = 0;
	}
	w[0]  = EM_DIAG_MAGIC;
	w[1]  = EM_DIAG_FORMAT;
	w[2]  = TAG_MOTR;
	w[3]  = millis();
	w[4]  = (uint32_t)(-here);
	w[5]  = 0;
	w[6]  = 0;
	w[7]  = ((uint32_t)r.duty_peak << 16) | r.duty_first;
	w[8]  = (uint32_t)r.start;
	w[9]  = (uint32_t)r.end;
	w[10] = em_frames_rx;
	w[11] = em_frames_tx;
	w[12] = ((uint32_t)r.outcome << 16) | r.ms;
	w[13] = (g_flash_boots << 16) | (g_boot & 0xFFFFu);
	w[14] = PM->RCAUSE.reg;
	w[15] = 2 + g_park_n;            /* step 2 = the first park attempt */
	if (g_park_n == 0) {
		diag_page(MOTOR_PAGE0 + 2, w, 16);
		trail_fhist(FHIST_PAGE);
		focus_hist_page(FOCUS_LAST_PAGE);
		trace_page(TRACE_PAGE0 + 2, 2, &r);
		norm_page();
	}
	g_park_n++;
}

/* Focus: drive the mechanism to a position the BODY asked for, on message
 * 0x04's 27-byte form, in the units message 0x06 reports.
 *
 * THE MAPPING.  Linear, anchored at the floor of the travel we advertise:
 *
 *     units  = FOCUS_EM06_LO + counts / FOCUS_COUNTS_PER_UNIT
 *     counts = (units - FOCUS_EM06_LO) * FOCUS_COUNTS_PER_UNIT
 *
 * with `counts` measured from the infinity stop, which is where homing puts
 * zero.  So the infinity end reports exactly 4144.
 *
 * Why the divide, when a slope of 1 would be simpler: the encoder runs at four
 * counts per protocol unit.  The advertised travel 4144..5632 spans 1488 =
 * 5952/4 exactly, which is the full mechanical travel in counts.
 *
 * A native lens converts through a non-linear per-lens ladder, which an adapter
 * with no electrical contact with the mounted lens cannot have.  A straight
 * line is the honest approximation: monotonic, continuous, and without the
 * doubling-back a ladder's descending branch shows.
 */
/* Ignore a commanded move smaller than this.  The encoder jitters a few counts
 * at rest, and a servo that re-runs for every one of them would drive the coils
 * continuously while the body holds focus still. */
/* Initial and equal-target moves still go through velocity/dwell checks. */

static uint16_t g_focus_moves;
static uint16_t g_focus_aborts;
static uint16_t g_stops_idle;   /* Stops that arrived with nothing running */
static uint16_t g_last_target;
static uint8_t  g_last_op;      /* enum em_focus_op of the running instruction */

/* The servo's abort hook reads this rather than the protocol flag: a Stop, a
 * Scan and a Drive all end the running leg, and only the main loop can tell
 * them apart afterwards.  g_abort_by_stop is which of those it was -- a Stop
 * is answered by the leg it stopped, the others are re-run from rest. */
static uint8_t  g_abort_by_stop;

/* An instruction the retarget hook could not apply to the running leg --
 * a Stop, a Scan, a Drive.  Handed forward so nothing is lost when the leg
 * unwinds. */

/* The last position reported, so the velocity history is a difference rather
 * than a level. */
static int32_t             g_last_reported;
static uint32_t            g_last_velocity_vd;

struct focus_rec {
	int32_t  delta;
	uint16_t ms;
	uint16_t target_u;    /* protocol units, as the body asked */
	uint16_t end_u;       /* protocol units, where we stopped */
	uint8_t  outcome;
	uint8_t  retargets;
	uint8_t  src;
};
static struct focus_rec g_focus_ring[FOCUS_LAST_N];
static uint16_t         g_focus_ring_n;


/* Publish where we are, into every message that carries it. */
/* Publish a position the caller has already read.  Split out so the servo's
 * pump can report without a second encoder transaction -- it reads once per
 * iteration and hands the value over. */
static void focus_report_at(int32_t counts)
{
    if (!focus_feedback_valid(counts)) return;
#ifdef EA9_FACTORY_AF
    factory_servo_sample_idle(counts);
    if (io_stop_motion()) return;
#endif
	/* Message 0x06 is the only message that carries the focus position.
	 *
	 * Anchored at the 4144 we ADVERTISE, not at the raw 4096.  The body
	 * issues its message 0x04 targets inside the travel we advertise, so
	 * reporting from a different floor would put our position and its
	 * targets 48 units apart. */
	int32_t ahead = focus_pred_ahead(&g_pred, counts, em_frame_period_ms);
	uint8_t moving;

	em_set_focus_position(focus_counts_to_em06(counts),
	                      focus_counts_to_em06(ahead));

	/* Moving, or at rest?  The forecast differing from the position is the
	 * same fact the body reads out of pl[2..3] against pl[20..21], so it is
	 * the honest source for the status byte -- a flag kept separately could
	 * contradict the very frame carrying it. */
	moving = (ahead != counts);
	em_set_motion(moving, moving ? (ahead > counts ? 0x02u : 0x04u) : 0x00u,
	              focus_counts_to_em06(counts));

	/* The velocity history the body follows a move with: one frame-to-frame
	 * difference per frame, newest last. */
	uint32_t frame = em_vd_edges;
	if (frame != g_last_velocity_vd) {
		em_push_velocity((counts - g_last_reported) / FOCUS_COUNTS_PER_UNIT);
		g_last_reported = counts;
		g_last_velocity_vd = frame;
	}

	/* And the same state in message 0x05, in units the body can use without
	 * knowing this lens: the subject distance, and the in-motion flag. */
	em_set_subject_distance(focus_distance_code(counts, ea9_profile_focal()),
	                        focus_distance_coarse(counts, ea9_profile_focal()),
	                        (uint8_t)(counts / 256));
	em_set_in_motion(moving);
}

/* Answer any 0x22 / 0x2E queries the body asked on the last message 0x04.
 * The conversion is the lens's own, which is the whole point of the query:
 * the body can name a distance without knowing these optics. */
static void focus_answer_queries(void)
{
    if (!g_homed || ea9_io_faults()) return;
	uint8_t  tag;
	uint16_t operand;
	uint8_t budget;

	/* An ISR may refill the queue after every pop.  Answer at most one
	 * queue's capacity per foreground pass so focus/Stop dispatch runs. */
	for (budget = 0; budget < EM_QUERY_Q && em_take_query(&tag, &operand); budget++) {
		if (tag == EM_REC_Q_POS2D) {
			em_post_query_answer(tag,
			        focus_distance_code(focus_em06_to_counts(operand),
			                            ea9_profile_focal()));
		} else {
			em_post_query_answer(tag,
			        focus_counts_to_em06(
			                focus_counts_for_code(operand,
			                                      ea9_profile_focal())));
		}
	}
}

/* The main loop's form: read, then publish. */
static void focus_report(void)
{
    if (!g_homed || ea9_io_faults()) return;
    focus_report_at(abs_encoder_track());
}

/* Translate camera operands through the independently tested module. */
static uint8_t focus_cmd_target(const struct em_focus_cmd *c, int32_t *out)
{
	int32_t here = 0;
	if (c->op == EM_OP_MOVE_REL || c->op == EM_OP_MOVE_DEFOCUS)
		here = abs_encoder_track();
	return ea9_af_resolve_target(c, here, ea9_profile_focal(),
	                             em_defocus_scale(), out);
}

/* The servo's other hook: has the body called the move off?
 *
 * A stop is NOT a retarget.  The body is not asking for a different position,
 * it is asking for the mechanism to stand still, so the servo returns
 * SERVO_ABORTED and the caller acknowledges rather than starting a new move.
 *
 * Consumed here, once.  Leaving it set would abort the next move as well. */
static uint8_t focus_abort(void)
{
	if (g_abort_pending || g_af_state.shutdown) return 1;
	/* Retargeting is bounded and is suspended during reversal braking.
	 * A command that cannot be consumed by that hook still interrupts this
	 * owner; in particular a Stop must not wait for a multi-second timeout. */
	struct em_focus_cmd c;
	if (!em_take_focus_cmd(&c)) return 0;
	g_abort_pending = 1;
	g_abort_by_stop = c.op == EM_OP_STOP;
	if (g_abort_by_stop) g_next_pending = 0;
	else { g_next = c; g_next_pending = 1; }
	return 1;
}

/* The servo's hook: has the body asked for somewhere else while we were on our
 * way?  The servo applies its own deadband, so a target rejected there has
 * still been consumed here -- which is correct, it means "no meaningful
 * change" -- and leaves the predictor at most retarget_min counts out. */
static uint8_t focus_retarget(int32_t *target)
{
	struct em_focus_cmd c;
	int32_t             want;

	if (!em_take_focus_cmd(&c)) {
		return 0;
	}

	/* THE INSTRUCTION THAT ARRIVED MID-MOVE.
	 *
	 * A new Move REPLACES the running one, and the leg carries straight on
	 * to the new target (autofocus.md 3.1 rule 4).  Only the latest
	 * instruction is answered, and here the latest one is the one this leg
	 * is now chasing -- so the single event at the end of the leg is its
	 * event, and the replaced target simply never gets one.  Nothing extra
	 * to suppress.
	 *
	 * Anything that is NOT a move to a position ends the leg instead: a
	 * Stop has no target to chase, and a Scan or a Drive is a different
	 * shape of motion that has to start from rest.  A Stop is reported by
	 * the leg it stopped; a Scan or a Drive is handed forward through
	 * g_next so the main loop can run it. */
	if (g_last_op == EM_OP_SCAN || g_last_op == EM_OP_DRIVE
	    || !focus_cmd_target(&c, &want)) {
		g_abort_pending = 1;
		g_abort_by_stop = (c.op == EM_OP_STOP);
		if (g_abort_by_stop) g_next_pending = 0;
		else {
			g_next         = c;
			g_next_pending = 1;
		}
		return 0;
	}

	g_last_op = c.op;
	g_last_target = c.target;
	focus_pred_retarget(&g_pred, want);
	*target = want;
	return 1;
}

/* One production dispatch boundary, also exercised by offline regressions.
 * Stop is acknowledged after a motion fault; it never clears that fault. */
static void focus_service(void)
{
	struct em_focus_cmd cmd;
	/* A newer received command supersedes a command handed forward by the
	 * previous owner. In particular, do not restart stale work before Stop. */
	if (em_take_focus_cmd(&cmd)) {
		g_next_pending = 0;
		focus_exec(&cmd);
	} else if (g_next_pending) {
		g_next_pending = 0;
		focus_exec(&g_next);
	}
}

/* Run one leg of motion and report it.  Everything that moves goes through
 * here, so the diagnostic page and the predictor cannot be bypassed.
 *
 * Returns the outcome.  It does NOT send an event -- who is entitled to an
 * event depends on which instruction this leg belonged to, and only the caller
 * knows that. */
static uint8_t focus_run(int32_t want, uint16_t target_u,
                         const struct servo_cfg *cfg)
{
	struct servo_result r;
	uint32_t w[16];
	int32_t  here, delta;
	unsigned i;

	if (!ea9_af_begin_motion(&g_af_state))
		return ea9_af_faulted(&g_af_state) ? g_af_state.fault_reason : SERVO_ABORTED;
	here  = abs_encoder_track();
	if (!focus_feedback_valid(here)) return SERVO_IO_FAULT;
	delta = want - here;

	/* Factory baseline uses target crossing, while the legacy backend uses
	 * speed/dwell checks. Neither is an optical focus-lock measurement. */

	/* The predictor's target is the COMMANDED position, not the servo's
	 * internal start+delta -- they differ by whatever the encoder moved
	 * between the two reads, and the field the body sees should be bounded
	 * by what it asked for. */
	focus_pred_begin(&g_pred, here, want, millis());
#ifdef EA9_FACTORY_AF
    factory_servo_move_to(want, cfg, &r);
#else
	servo_move_rel(delta, cfg, &r);
#endif
	ea9_af_end_motion(&g_af_state);
	/* Unsafe feedback faults inhibit later drive. A healthy bounded deadline
	 * or no-drive resolution result is actuator termination, not focus lock. */
	if (ea9_af_note_result(&g_af_state, r.outcome) || g_af_state.shutdown) motor_release();
	focus_pred_end(&g_pred);
	focus_report();

	for (i = 0; i < 16; i++) {
		w[i] = 0;
	}
	w[0]  = EM_DIAG_MAGIC;
	w[1]  = EM_DIAG_FORMAT;
	w[2]  = TAG_FOCS;
	w[3]  = millis();
	w[4]  = (uint32_t)delta;
	w[5]  = ((uint32_t)target_u << 16) | focus_counts_to_em06(r.end);
	w[6]  = ((uint32_t)em_t04_target << 16)
	        | ((uint32_t)em_frame_period_ms << 8)
	        | (em_frame_period_n > 255u ? 255u : em_frame_period_n);
	w[7]  = ((uint32_t)r.duty_peak << 16) | r.duty_first;
	w[8]  = (uint32_t)r.start;
	w[9]  = (uint32_t)r.end;
	w[10] = em_frames_rx;
	w[11] = em_frames_tx;
	w[12] = ((uint32_t)r.outcome << 16) | r.ms;
	w[13] = (g_flash_boots << 16) | (g_boot & 0xFFFFu);
	w[14] = ((uint32_t)em_focus_n << 16) | g_focus_moves;
	w[15] = ((uint32_t)g_last_op << 24) | ((uint32_t)r.retargets << 16)
	        | em_t04_n;
	if (g_focus_moves < FOCUS_PAGES) {
		diag_page(FOCUS_PAGE[g_focus_moves], w, 16);
	}

	{
		struct focus_rec *rec =
			&g_focus_ring[g_focus_ring_n % FOCUS_LAST_N];

		rec->delta     = delta;
		rec->ms        = r.ms;
		rec->target_u  = target_u;
		rec->end_u     = focus_counts_to_em06(r.end);
		rec->outcome   = r.outcome;
		rec->retargets = r.retargets;
		rec->src       = g_last_op;
		g_focus_ring_n++;
	}

	g_focus_moves++;
	g_last_target = target_u;
	if (io_stop_motion()) return SERVO_IO_FAULT;
	return r.outcome;
}


/* ------------------------------------------------------------------------
 * SCAN -- the two-leg instruction (autofocus.md 3.3).
 *
 * The body asks for focus to cross a window [B .. A] at a steady speed so it
 * can sample the image continuously while focus moves.  That takes two
 * movements:
 *
 *     position ->   run-up        window [B .. A]         run-out
 *                 |<------>|<========================>|<------>|
 *     leg 1:  fast move to the start of the run-up
 *     leg 2:                  constant speed across the whole window ------>
 *
 * The run-up exists so the mechanism is ALREADY at speed when it crosses the
 * first endpoint, and the run-out so it is still at speed when it leaves the
 * last one.  Acceleration and deceleration then happen outside the window,
 * where the body is not measuring.
 *
 * NOT YET OBSERVED ON AN a9 II.  Across every session captured so far that
 * body has sent only Move and Stop records -- 356 Moves and 59 Stops in one
 * 265-second run (NOTES.md 79), and no Scan at all.  This branch is written
 * from the protocol rather than from traffic, so it is the one part of the
 * focus path that has never executed on hardware.
 */
#define SCAN_RUNUP_COUNTS   300
#define SCAN_RUNOUT_COUNTS  240

static void focus_scan(const struct em_focus_cmd *c)
{
	int32_t a, b, lo, hi, start, finish;
	uint8_t outcome;

	/* The endpoint form gives two positions; the centred form gives a
	 * centre and the extents either side of it. */
	if (c->scan_flags & 0x01u) {
		int32_t centre = focus_em06_to_counts(c->scan_centre);

		hi = centre + (int32_t)c->scan_a * FOCUS_COUNTS_PER_UNIT;
		lo = centre - (int32_t)c->scan_b * FOCUS_COUNTS_PER_UNIT;
	} else {
		a  = focus_em06_to_counts(c->scan_a);
		b  = focus_em06_to_counts(c->scan_b);
		lo = (a < b) ? a : b;
		hi = (a < b) ? b : a;
	}
	if (lo < 0) {
		lo = 0;
	}
	if (hi > FOCUS_TRAVEL_COUNTS) {
		hi = FOCUS_TRAVEL_COUNTS;
	}
	if (hi < lo) {
		hi = lo;
	}

	/* Direction.  Bits 0-2 = 6 reverses the sweep; bit 3 asks for whichever
	 * end of the window is nearer where focus already is, which saves the
	 * longer approach. */
	{
		int32_t here    = abs_encoder_track();
		uint8_t reverse = ((c->scan_flags & 0x07u) == 6u);

		if (c->scan_flags & 0x08u) {
			reverse = ((here - lo) > (hi - here));
		}
		if (reverse) {
			start  = hi + SCAN_RUNUP_COUNTS;
			finish = lo - SCAN_RUNOUT_COUNTS;
		} else {
			start  = lo - SCAN_RUNUP_COUNTS;
			finish = hi + SCAN_RUNOUT_COUNTS;
		}
	}
	if (start < 0) {
		start = 0;
	} else if (start > FOCUS_TRAVEL_COUNTS) {
		start = FOCUS_TRAVEL_COUNTS;
	}
	if (finish < 0) {
		finish = 0;
	} else if (finish > FOCUS_TRAVEL_COUNTS) {
		finish = FOCUS_TRAVEL_COUNTS;
	}

	em_set_scan_state(EM_SCAN_ACCEPTED);

	/* Leg 1: get to the run-up point, at whatever speed suits.  Wait until
	 * it is at rest before the sweep -- focus_run is blocking, so this is
	 * the ordering by construction. */
	outcome = focus_run(start, focus_counts_to_em06(start), &MOTION_PROFILE);
	if (!ea9_af_outcome_arrived(outcome) || g_next_pending) {
		em_set_scan_state(EM_SCAN_IDLE);
        if (outcome != SERVO_OK) {
            uint8_t event = ea9_af_completion_event(&g_af_state, EM_OP_SCAN, outcome, g_abort_by_stop);
            if (event) em_post_event(event, event == EM_REC_STOP ? 0x01u : 0x00u);
        }
		return;                 /* replaced or stopped: no event */
	}

	/* Leg 2: the sweep.  The scan speed code's magnitude is in the low bits
	 * of rec[4]; the unit is UNKNOWN, so the candidate maps it onto its own
	 * configured velocity range. This mapping remains unqualified. */
	em_set_scan_state(EM_SCAN_SWEEPING);
	{
		struct servo_cfg sweep = MOTION_PROFILE;
#ifndef EA9_FACTORY_AF
		uint16_t         mag   = c->scan_speed & 0x7Fu;

		sweep.v_cruise = SCAN_V_MIN
		                 + (int32_t)((uint32_t)mag
		                             * (SCAN_V_MAX - SCAN_V_MIN) / 0x7Fu);
		sweep.stop_ms  = SCAN_STOP_MS;
#endif
		/* Factory baseline uses its recovered fixed speed staircase. The
		 * upstream scan-speed mapping is deliberately not mixed into it. */
		outcome = focus_run(finish, focus_counts_to_em06(finish), &sweep);
	}

	if (ea9_af_outcome_arrived(outcome) && !g_next_pending) em_scan_finish();
    else em_set_scan_state(EM_SCAN_IDLE);
    uint8_t event = ea9_af_completion_event(&g_af_state, EM_OP_SCAN, outcome, g_abort_by_stop);
    if (event) em_post_event(event, event == EM_REC_STOP ? 0x01u : 0x00u);
}

/* ------------------------------------------------------------------------
 * DRIVE -- run toward one end at a given speed (autofocus.md 3.4).
 *
 * NOT YET OBSERVED ON AN a9 II either, and not observed on any wire at all.
 */
static void focus_drive(const struct em_focus_cmd *c)
{
	struct servo_cfg drv = MOTION_PROFILE;
	int32_t          want;
#ifndef EA9_FACTORY_AF
	uint16_t         mag = (c->drive_vel < 0)
	                       ? (uint16_t)(-c->drive_vel) : (uint16_t)c->drive_vel;
#endif

	/* Zero or negative runs to the lower limit, positive to the upper. */
	want = (c->drive_vel > 0) ? FOCUS_TRAVEL_COUNTS : 0;

#ifndef EA9_FACTORY_AF
	/* "The speed has a floor, so any non-zero request moves at a useful
	 * rate, and a ceiling at the lens's maximum." */
	if (mag > 0x7FFFu) {
		mag = 0x7FFFu;
	}
	drv.v_cruise = SCAN_V_MIN
	               + (int32_t)((uint32_t)mag
	                           * (SCAN_V_MAX - SCAN_V_MIN) / 0x7FFFu);
	drv.stop_ms  = SCAN_STOP_MS;
#endif

    uint8_t result = focus_run(want, focus_counts_to_em06(want), &drv);
    uint8_t event = ea9_af_completion_event(&g_af_state, EM_OP_DRIVE, result, g_abort_by_stop);
    if (event == EM_REC_STOP) em_post_event(event, 0x01u);
	if (event == EM_REC_DRIVE) {
		/* Drive has no end of its own short of the limit, so its event
		 * carries the top six bits of the record's rec[1] and a 4-byte
		 * tail rather than the usual 2. */
		em_post_event(EM_REC_DRIVE, (uint8_t)(c->drive_param >> 2));
	}
}

/* Act on one instruction from the body. */
static void focus_exec(const struct em_focus_cmd *c)
{
	int32_t want;
	uint8_t outcome;

    if (c->op == EM_OP_STOP) {
        uint8_t event = ea9_af_completion_event(&g_af_state, EM_OP_STOP, SERVO_ABORTED, 1);
        if (event) { motor_release(); em_set_scan_state(EM_SCAN_IDLE); em_post_event(event, 0x01u); g_stops_idle++; }
        return;
    }
    if (!g_homed || g_af_state.shutdown || ea9_af_faulted(&g_af_state)) return;

	g_last_op       = c->op;
	g_abort_pending = 0;
	g_abort_by_stop = 0;

	switch (c->op) {

	case EM_OP_SCAN:
		focus_scan(c);
		return;

	case EM_OP_DRIVE:
		focus_drive(c);
		return;

	default:
		break;
	}

	if (!focus_cmd_target(c, &want)) {
		return;
	}
	outcome = focus_run(want, c->target, &MOTION_PROFILE);

    if (outcome == SERVO_ABORTED) g_focus_aborts++;
    uint8_t event = ea9_af_completion_event(&g_af_state, c->op, outcome, g_abort_by_stop);
    if (event) em_post_event(event, event == EM_REC_STOP ? 0x01u : 0x00u);

}

/* The last few moves, oldest first, written once when the bus goes quiet. */
static void focus_hist_page(uint32_t page)
{
	uint32_t w[16];
	unsigned i;

	for (i = 0; i < 16; i++) {
		w[i] = 0;
	}
	w[0] = EM_DIAG_MAGIC;
	w[1] = EM_DIAG_FORMAT;
	w[2] = TAG_FLST;
	w[3] = millis();
	w[4] = ((uint32_t)g_focus_ring_n << 16) | g_focus_moves;

	for (i = 0; i < FOCUS_LAST_N; i++) {
		unsigned k = (g_focus_ring_n >= FOCUS_LAST_N)
		             ? (g_focus_ring_n + i) % FOCUS_LAST_N : i;
		const struct focus_rec *rec = &g_focus_ring[k];

		w[5 + i * 3] = ((uint32_t)rec->outcome << 24)
		               | ((uint32_t)rec->retargets << 16) | rec->ms;
		w[6 + i * 3] = (uint32_t)rec->delta;
		w[7 + i * 3] = ((uint32_t)rec->target_u << 16) | rec->end_u;
	}
	/* w[5..13] are the three records; w[14] is the only word left, so the
	 * stop counters are BYTES in it, beside the newest record's source:
	 * stops that arrived with nothing running, stops in total, and moves
	 * actually cut short by one.  The 8-bit total saturates -- the NORM
	 * page carries em_stop_n in full, this copy is here so one page tells
	 * the whole story. */
	w[14] = ((uint32_t)(g_stops_idle & 0xFFu) << 24)
	        | ((uint32_t)(em_stop_n & 0xFFu) << 16)
	        | ((uint32_t)(g_focus_aborts & 0xFFu) << 8)
	        | g_focus_ring[(g_focus_ring_n + FOCUS_LAST_N - 1) % FOCUS_LAST_N].src;
	w[15] = ((uint32_t)em_focus_n << 16) | em_t04_n;
	diag_page(page, w, 16);
}

int main(void)
{
	int      hs_marked = 0;
	int      caps_flushed = 0;
	int      caps_written = 0;
	unsigned step = 0;
	int      quiet = 0;

	/* Pins FIRST, before the clocks.
	 *
	 * PORT needs no clock setup -- it is fed from the AHB/APBB clocks that
	 * are already running out of reset -- so this is valid at the very
	 * first instruction and costs nothing.
	 *
	 * It matters because at reset every pin is an INPUT WITH NO PULL.
	 * Five of these drive something: PA10 is the lens chip select and PA23
	 * is read by the body.  A floating CMOS input at the far end can sit
	 * near its threshold and oscillate, so "undriven for seven
	 * milliseconds" is an electrical hazard, not a style question.  The
	 * stock drives them within microseconds of reset.
	 *
	 * Measured to make no difference to boot or shutdown on the a9 II, so
	 * this is chosen on principle, not on evidence -- which is why it is
	 * one ordering and not a switch. */
	board_init_pins();

	clock_init();
	/* A failed core-clock transition has no trustworthy SysTick timing.
	 * Leave GPIO-released coils inhibited; do not start protocol or homing. */
	if (ea9_io_faults()) { motor_inhibit(); for (;;) { __WFI(); } }
	delay_init();

	{
		uint32_t rcause = PM->RCAUSE.reg;

		/* Tally FIRST: it says which slot this boot owns. */
		g_flash_boots = diag_boot_tally(rcause);
		g_boot = diag_begin(g_flash_boots);
		trail_set_boot(g_boot, g_flash_boots);
	}

	/* main's one addition on top of atmel_start_init's pin state: PA16
	 * high.  Deliberately NOT moved up with board_init_pins() -- it stays
	 * ahead of motor_init() exactly as before, so the window in which PA16
	 * is high while the motor PWM is unconfigured does not grow.  Until
	 * here PA16 sits low, which is atmel_start_init's own value for it. */
	PORT->Group[0].OUTSET.reg = (1u << 16);

	motor_init();
	motor_release();
	abs_encoder_init();
	vdd_init();
	(void)io_stop_motion();              /* coils stay idle until the test */
	/* Reject corrupt profiles before any handshake or motion. */
	if (!ea9_profile_load()) { for (;;) { __WFI(); } }

	trail_chk(18);
	build_marker_page(19);

	em_set_park_handler(park_to_infinity);
	em_set_powerdown_handler(powerdown_signal);

	em_init();
	diag_tally_mark(DIAG_MARK_BUSUP, 0);

	abs_encoder_set_reference();
	abs_encoder_track_reset();

	for (;;) {
		em_poll();

		/* If the handshake has not completed by two seconds it is not
		 * going to.  The motor pages are then free -- no motor step can
		 * run without a handshake -- so the frames the body did send go
		 * there.  They have never been seen. */
		/* Not "after two seconds": in a failing boot em_init does not
		 * return until 4.6 s and the frames arrive after that, so a
		 * fixed deadline flushes an empty buffer.  Wait until the bus
		 * has been up and then quiet for half a second. */
		if (!caps_flushed && !em_handshake_done && em_t_init_done
		    && (uint32_t)(millis() - (em_t_last_frame ? em_t_last_frame
		                                              : em_t_init_done))
		       >= 500u) {
			unsigned k;

			uint32_t w[16];

			caps_flushed = 1;
			for (k = 0; k < em_pre_used && k < EM_PRE_SLOTS; k++) {
				trail_cap_pre(TRACE_PAGE0 + k, k);
			}

			/* And the timing of the failure, on a page the motor
			 * would have used had it run. */
			for (k = 0; k < 16; k++) {
				w[k] = 0;
			}
			w[0]  = EM_DIAG_MAGIC;
			w[1]  = EM_DIAG_FORMAT;
			w[2]  = TAG_FAIL;
			w[3]  = millis();
			w[4]  = em_t_first_vd;
			w[5]  = em_vd_edges;
			/* two timings per word: times are well under 65 s and
			 * there is no spare word left on this page. */
			w[6]  = (em_t_cs_first_high & 0xFFFFu)
			        | (em_first_window_ms << 16);
			w[7]  = em_t_init_done;
			w[8]  = em_t_first_frame;
			w[9]  = (em_t_last_frame & 0xFFFFu)
			        | (em_t_first_byte << 16);
			w[10] = em_frames_rx;
			w[11] = em_frames_tx;
			/* The three that separate "body silent" from "body
			 * talking, us deaf". */
			w[12] = em_cs_edges;
			/* total, and how many of those arrived INSIDE the first
			 * window -- the two call for opposite fixes. */
			w[13] = (em_rx_bytes & 0xFFFFu)
			        | ((em_rx_bytes_at_close - em_rx_bytes_at_open) << 16);
			w[14] = ((uint32_t)em_pre_used << 24)
			        | ((uint32_t)em_rx_status << 8)
			        | (em_rx_errors & 0xFFu);
			/* spare high bit of the status word, NOT of the VD
			 * timestamp -- packing it there would have corrupted
			 * a real measurement to carry one flag. */
			w[14] |= (uint32_t)em_init_frame_rescued << 31;
			w[15] = PM->RCAUSE.reg;
			diag_page(MOTOR_PAGE0, w, 16);

			/* The ids in order, on their own page: with no frames
			 * at all the quiet detector never fires, so this run
			 * was the only one with no id log. */
			quiet_idlog_page();
		}

		if (!hs_marked && em_handshake_done) {
			hs_marked = 1;
			diag_tally_mark(DIAG_MARK_HANDSHAKE, 0);
		}

		/* The transfer-window captures, once the handshake is over so
		 * the init frames are in them too.  One page each; they are
		 * written once and never again. */
		if (!caps_written && em_handshake_done && millis() >= 3000u) {
			unsigned k;

			caps_written = 1;
			for (k = 0; k < CAP_PAGES && k < em_cap_used; k++) {
				trail_cap(CAP_PAGE0 + k, k);
			}
			trail_m08(M08_PAGE);
		}

		/* --- has the body stopped talking? ---
		 *
		 * Observation only.  The 500 ms-silence PARK that used to live
		 * here is GONE: it was invented when it looked as though this
		 * body never sent message 0x16, and once 0x16 turned out to
		 * arrive on every proper power-off it was a second, redundant
		 * trigger for the same action -- and it fired in builds that
		 * were supposed to have no park at all, which quietly ruined
		 * the control in a measurement run.
		 *
		 * The tick pages that measured how long the adapter stayed
		 * powered afterwards are gone with the rest of the shut-down
		 * record; what is left here is the two writes that have to
		 * happen before power goes away. */
		if (em_t_last_frame
		    && (uint32_t)(millis() - em_t_last_frame) >= QUIET_MS) {
			if (!quiet) {
				quiet = 1;
				quiet_idlog_page();
			}
			/* The histogram is final only once the body is really
			 * gone.  Writing it at the FIRST 100 ms gap gave a
			 * histogram of the first 35 seconds of an 85-second
			 * session -- the body pauses for a tenth of a second
			 * whenever metering times out, and the once-only guard
			 * then locked that partial count in.  The park is the
			 * normal writer; this is the fallback for a run that
			 * is cut off, so it waits for a silence no metering
			 * pause produces. */
			if ((uint32_t)(millis() - em_t_last_frame)
			    >= NORM_QUIET_MS) {
				norm_page();
			}
		} else if (quiet && em_t_last_frame
		           && (uint32_t)(millis() - em_t_last_frame) < QUIET_MS) {
			quiet = 0;      /* it came back; that was a hiccup */
		}

		/* Home once, then serve whatever focus targets arrive.
		 *
		 * The gate is the completed HANDSHAKE, not a wall
		 * clock: `millis() >= 4000` held the mechanism still for four
		 * seconds of every boot and guarded nothing (NOTES.md 112). */
		if (!g_af_state.shutdown && !ea9_af_faulted(&g_af_state) && em_handshake_done && step == 0
		    && HOME_GATE_OPEN()) {
			motor_home();
			focus_report();
			step = 1;
		}
		if (step == 1) {
			/* Report first: the body is told where we are on every
			 * frame, whether or not it ever commands a move. */
			focus_report();
			focus_answer_queries();

			/* An instruction the retarget hook handed forward
			 * because it could not be applied to a running leg. */
			focus_service();
		} else if (ea9_af_faulted(&g_af_state)) {
			/* Initialization faults can inhibit homing before step 1.
			 * Stop remains an idle acknowledgement in that state too. */
			focus_service();
		}
	}
}
