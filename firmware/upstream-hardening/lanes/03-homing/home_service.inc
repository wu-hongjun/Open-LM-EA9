/* No unsolicited retry after cancellation; faults remain closed until reboot.
 * Two attempts total per boot, including cancellation. Capture completion does
 * not grant a retry; only a fresh motion request may retry a cancelled home. */
static void home_service(void)
{
    uint8_t fresh;
    if (g_homed || g_aborted || em_shutdown_requested()) return;
    if (!em_handshake_done) { g_next_pending = 0; return; }
    fresh = home_command();
    if (g_home_attempts >= HOME_ATTEMPTS || g_home_state == HOME_FAILED ||
        (g_home_state == HOME_CANCELLED && !fresh)) return;
    ++g_home_attempts;
    g_home_session = em_session_generation();
    g_home_state = HOME_ACTIVE;
    motor_home();
}
