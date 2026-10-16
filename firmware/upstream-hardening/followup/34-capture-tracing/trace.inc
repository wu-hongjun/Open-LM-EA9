/* RAM-only ownership observations; no whole frame or operand is retained.
 * The low identity byte is the owning request's sequence for control TX,
 * and the actual frame sequence for status/shutdown TX. */
enum em_trace_flag {
    ET_RAW=1, ET_CONTROL=2, ET_SHUTDOWN=4, ET_PHASE=8,
    ET_SLOT=16, ET_PENDING=32, ET_STATUS=64, ET_RESULT=128
};
static uint16_t em_trace_identity(const uint8_t *p)
{
    return (uint16_t)(((uint16_t)p[5] << 8) | p[4]);
}
static uint8_t em_trace_flags(void)
{
    return (uint8_t)((g_shutdown.state != EM_SD_IDLE ? ET_SHUTDOWN : 0)
        | (g_owner.phase << 3) | (g_owner.active << 4)
        | (g_owner.pending << 5)
        | (g_owner.status_enabled << 6));
}
static void em_trace(uint8_t kind, uint16_t identity, uint8_t flags,
                     uint32_t session)
{
    st_note(kind, (uint8_t)(identity >> 8), flags, (uint8_t)identity,
            (uint16_t)session, (uint16_t)(session >> 16), millis());
}
