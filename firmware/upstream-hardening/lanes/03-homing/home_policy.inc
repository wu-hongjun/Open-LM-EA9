/* Included in main.c after pump; software readiness, not physical calibration. */
enum home_state { HOME_UNTRIED, HOME_ACTIVE, HOME_READY, HOME_CANCELLED, HOME_FAILED };
static enum home_state g_home_state;
static uint8_t g_home_attempts;
static uint32_t g_home_session;
#define HOME_ATTEMPTS 2u
/* Finite instruction-work fallback, NOT a measured electrical time limit. */
#define HOME_POLL_LIMIT 1000000u

/* Same GPIO detach/output convention as st_fail, without peripheral waits.
 * Driver-wide sticky inhibition closes interrupt-versus-remux races. */
static void home_cutoff(void)
{
    motor_emergency_release();
}
static void motion_shutdown_inhibit(void)
{
    g_aborted = 1;
    motor_inhibit();
}
/* Preserve the latest motion for service after successful reference, while a
 * Stop invalidates it. A new session invalidates old-session motion outright. */
static uint8_t home_command(void)
{
    struct em_focus_cmd c;
    if (!em_take_focus_cmd(&c)) return 0;
    if (c.op == EM_OP_STOP) {
        g_next_pending = 0;
        g_home_state = HOME_CANCELLED;
        home_cutoff();
        em_post_event(EM_REC_STOP, 1u);
        return 0;
    }
    g_next = c;
    g_next_session = em_session_generation();
    g_next_pending = 1;
    return 1;
}
static uint8_t home_cancel_requested(void)
{
    if (g_aborted || em_shutdown_requested() || !em_handshake_done ||
        em_session_generation() != g_home_session) {
        g_next_pending = 0;
        g_home_state = HOME_CANCELLED;
    } else {
        (void)home_command();
    }
    return g_home_state == HOME_CANCELLED;
}
