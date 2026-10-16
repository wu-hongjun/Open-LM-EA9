/* Bounded, write-once diagnostics for one upstream C camera experiment. */
#ifndef EA9_STARTUP_TRACE_H
#define EA9_STARTUP_TRACE_H
#include <stdint.h>
#define ST_FLASH_BASE 0x9c00u
#define ST_FLASH_END  0xa000u
#define ST_PAGE_BYTES 64u
#define ST_PAGE_COUNT 16u
#define ST_EVENTS 32u
enum st_event {
    ST_STAGE=1, ST_CS=2, ST_RX=3, ST_TX=4, ST_HANDSHAKE=5, ST_FAULT=6,
    ST_WINDOW_PRESERVED=7, ST_BAD_RX=8, ST_SHUTDOWN=9, ST_CAPABILITY=10,
    ST_OWNER_CS=11, ST_OWNER_OFFER=12, ST_OWNER_TAKE=13, ST_TX_START=14,
    ST_TX_RETURN=15, ST_SHUTDOWN_ADMIT=16, ST_OWNER_COMPLETE=17, ST_OWNER_PHASE=18
};
enum st_stage {
    ST_MAIN=1, ST_CLOCK=2, ST_TICK=3, ST_ENCODER=4, ST_ADC=5, ST_MOTOR=6,
    ST_UART=7, ST_WAIT_RISE=8, ST_WAIT_FALL=9, ST_EIC=10,
    ST_BUS_READY=11, ST_REFERENCE=12, ST_LOOP=13, ST_CONNECTED=14
};
enum st_fault {
    ST_CLOCK_WAIT=1, ST_ENCODER_WAIT=2, ST_ADC_WAIT=3, ST_MOTOR_WAIT=4,
    ST_UART_WAIT=5, ST_EIC_WAIT=6, ST_TICK_WAIT=7, ST_CS_RISE_WAIT=8,
    ST_CS_FALL_WAIT=9, ST_RX_DRAIN_FAULT=10, ST_HOME_FAILED=11,
    ST_MOTOR_BUDGET=12, ST_SERVO_BUDGET=13, ST_SERVO_RUNAWAY=14,
    ST_SERVO_WRONG_WAY=15, ST_ENCODER_OVERFLOW=16
};
/* Hardware boundary. The host tests supply inert flash and IRQ implementations. */
uint32_t st_lock(void);
void st_unlock(uint32_t prior);
int st_read_page(uint32_t address, uint8_t out[ST_PAGE_BYTES]);
int st_write_page(uint32_t address, const uint8_t page[ST_PAGE_BYTES]);
void st_init(void);
void st_note(uint8_t kind, uint8_t id, uint8_t cls, uint8_t seq,
             uint16_t length, uint16_t operand, uint32_t ms);
/* Narrow diagnostic-only paths; payloads retain the exact v3 byte layout. */
void st_summary(uint8_t kind, uint8_t id, uint32_t ms);
void st_record(uint32_t ms, uint32_t identity, uint32_t payload);
#ifndef STARTUP_TRACE_IMPLEMENTATION
#define st_note(k,id,cls,seq,len,operand,ms) \
    (__builtin_constant_p(k) ? \
      ((((uint8_t)(k))==ST_STAGE || ((uint8_t)(k))==ST_CS || ((uint8_t)(k))==ST_RX || ((uint8_t)(k))==ST_TX || ((uint8_t)(k))==ST_CAPABILITY) \
       ? st_summary((k),(id),(ms)) \
       : st_record((ms),(uint32_t)(uint8_t)(k)|((uint32_t)(uint8_t)(id)<<8)|((uint32_t)(uint8_t)(cls)<<16)|((uint32_t)(uint8_t)(seq)<<24), \
           (uint32_t)(uint16_t)(len)|((uint32_t)(uint16_t)(operand)<<16))) \
      : st_note((k),(id),(cls),(seq),(len),(operand),(ms)))
#endif
/* Main/fault context only. allowed=0 MUST NOT touch NVM. Never called in RX IRQ. */
void st_flush(int allowed, uint32_t ms, uint32_t rx_bytes,
              uint16_t rx_errors, uint16_t uart_status, uint8_t pins);
uint32_t st_crc32(const uint8_t *data, unsigned length);
/* Preserve a plausible first init-frame prefix already received at CS rise. */
int st_preserve_first_window(const uint8_t *data, unsigned length);
void st_fail(uint8_t fault) __attribute__((noreturn));
/* Iteration bound is a fail-stop budget, not a calibrated timeout. */
#ifndef ST_WAIT_BUDGET
#define ST_WAIT_BUDGET 4194304u
#endif
#define ST_WAIT_WHILE(condition, fault) do { \
    uint32_t st_budget_ = ST_WAIT_BUDGET; \
    while (condition) { if (--st_budget_ == 0) st_fail(fault); } \
} while (0)
enum st_terminal_kind { ST_VD_LOW=1, ST_VD_TIMEOUT=2, ST_PA23=3, ST_TAIL_DONE=4, ST_TERMINAL_FAULT=5 };
/* Main terminal context only: UART disabled or emergency motor cutoff already done. */
void st_terminal(uint8_t kind, uint8_t value, uint32_t ms);
#endif

/* RAM-only first inhibit reason, never a flush. */
void st_inhibit_fault(uint8_t reason);
