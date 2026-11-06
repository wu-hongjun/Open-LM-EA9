#ifndef EA9_STARTUP_PROBE_H
#define EA9_STARTUP_PROBE_H

#include <stdbool.h>
#include <stdint.h>

enum { PROBE_BASE = 0x9c00, PROBE_END = 0xa000, PROBE_PAGE = 64,
       PROBE_WINDOW = 256, PROBE_REPLY = 210 };

enum probe_flag {
    BUS_READY = 1, FINAL_ECHO = 2, STATUS_PAIR = 4, CS_RISE = 8,
    CS_FALL = 16, FIRST_PREFIX = 32, CAPABILITIES = 64, IDENTITY = 128
};
enum probe_reason {
    FIRST_CLOSE_TIMEOUT = 1, INACTIVITY, INIT_DEADLINE, PERIPHERAL_FAULT,
    TX_FAULT, SHUTDOWN
};
enum probe_tx { TX_BUSY, TX_ABORTED, TX_SHIFTED, TX_RELEASED };

struct probe_mark { uint32_t ms; uint16_t length; uint8_t id; };
struct probe_request { struct probe_mark mark; uint8_t frame[PROBE_WINDOW]; };
struct probe {
    struct probe_mark last_rx, paired_rx, paired_tx, last_txc, first_normal;
    struct probe_request pending;
    uint32_t activity_ms;
    uint16_t invalid, drops, uart_errors, vd;
    uint8_t flags, status_seq;
    bool status_due, has_activity;
};

void probe_count(uint16_t *counter);
void probe_open(struct probe *p, bool preserved_prefix);
void probe_close(struct probe *p, const uint8_t *bytes, uint16_t count, bool invalid, uint32_t now);
bool probe_take(struct probe *p, struct probe_request *request);
uint16_t probe_reply(const struct probe_request *request, uint8_t reply[PROBE_REPLY]);
bool probe_sent(struct probe *p, const struct probe_request *request, uint16_t length,
                enum probe_tx outcome, uint32_t txc_ms);
void probe_vd(struct probe *p);
uint16_t probe_status(uint8_t id, uint8_t seq, uint8_t reply[PROBE_REPLY]);
enum probe_reason probe_timeout(const struct probe *p, uint32_t now, uint32_t ready_ms);
void probe_encode(const struct probe *p, uint8_t slot, enum probe_reason reason,
                  uint32_t now, uint8_t page[PROBE_PAGE]);
bool probe_persist(const struct probe *p, enum probe_reason reason, uint32_t now);

bool probe_read_page(uint32_t address, uint8_t page[PROBE_PAGE]);
bool probe_write_page(uint32_t address, const uint8_t page[PROBE_PAGE]);

#endif
