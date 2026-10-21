/* Included by startup_trace.c: no hardware/NVM operations during checkpoint.
 * Only a completed foreground checkpoint, NOT an exact crash-time snapshot.
 * Schema 1 binds the existing 48-byte v3 summary layout. */
#define ST_RETAINED_MAGIC 0x31523945u
static struct {
    uint32_t magic, crc;
    struct summary summary;
} retained
#ifndef ST_HOST
    __attribute__((section(".noinit.st_retained"), aligned(4)))
#endif
;

void st_checkpoint(uint32_t ms)
{
    uint32_t key=st_lock();
    retained.magic=0;
    __asm__ volatile ("" ::: "memory");
    retained.summary=s;
    retained.summary.ms=ms;
    st_unlock(key);
    retained.crc=st_crc32((const uint8_t *)&retained.summary,48);
    __asm__ volatile ("" ::: "memory");
    retained.magic=ST_RETAINED_MAGIC;
}

/* Call once after st_init, before enabling protocol or motor hardware.
 * SAM D21 RCAUSE: POR=1, BOD12=2, BOD33=4, EXT=16, WDT=32, SYST=64.
 * Mixed cold/external causes never authorize retained RAM. The caller owns
 * fail-stop disposition on watchdog/system reset, even with invalid RAM. */
int st_boot_record(uint8_t reset_cause)
{
    struct page p={.type=5,.n=1,.reserved=reset_cause};
    if (crash_latched) { retained.magic=0; return 1; }
    if ((reset_cause==32 || reset_cause==64)
        && retained.magic==ST_RETAINED_MAGIC
        && retained.crc==st_crc32((const uint8_t *)&retained.summary,48)) {
        p.chunk=1;
        memcpy(p.data,&retained.summary,48);
    }
    /* Consumed before any NVM access: failed/torn writes cannot replay it. */
    retained.magic=0;
    __asm__ volatile ("" ::: "memory");
    if (!append(&p)) return 1;
    r_cohort=r_next_page+1;
    return (reset_cause & (32u|64u)) != 0;
}
