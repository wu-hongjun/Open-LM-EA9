/* SPDX-License-Identifier: MIT */
#include "em_arbitration.h"
void em_arb_open(volatile struct em_arbitration *a)
{
    a->receiving = 1;
    ++a->receive_epoch;
    a->status = 0; /* An interrupted pair is superseded, never resumed stale. */
}
void em_arb_close(volatile struct em_arbitration *a) { a->receiving = 0; }
void em_arb_request(volatile struct em_arbitration *a, uint8_t id)
{
    a->status = 0;
    if (id == 0x16) a->shutdown = 1;
    if (id == 0x0a && a->ready && !a->boot_pending && !a->capture) { a->capture = 1; a->capture_clocked = 0; }
    if (id == 1 && !a->off && !a->shutdown) {
        ++a->session_epoch;
        a->boot_pending = 1;
        a->ready = 0;
        a->capture = 0;
        a->capture_clocked = 0;
    }
}
void em_arb_frame(volatile struct em_arbitration *a, uint8_t sequence, uint8_t control_pending)
{
    if (a->capture == 1 && a->ready && !a->off && !a->shutdown) a->capture_clocked = 1;
    if (!a->ready || a->receiving || a->transmitting || a->shutdown || a->off || a->capture || control_pending) return;
    a->sequence = sequence;
    a->status = EM_TX_STATUS05;
}
uint8_t em_arb_begin(volatile struct em_arbitration *a, uint8_t kind, uint8_t wire_busy, uint8_t control_pending)
{
    if (a->off || wire_busy || a->receiving || a->transmitting) return 0;
    if (a->shutdown && kind != EM_TX_SHUTDOWN) return 0;
    if (kind == EM_TX_STATUS05 || kind == EM_TX_STATUS06) {
        if (!a->ready || a->capture || control_pending || a->status != kind) return 0;
    }
    a->transmitting = 1;
    a->transmit_epoch = a->receive_epoch;
    return 1;
}
void em_arb_end(volatile struct em_arbitration *a, uint8_t kind, uint8_t sent)
{
    a->transmitting = 0;
    if (kind == EM_TX_STATUS05 || kind == EM_TX_STATUS06) {
        a->status = sent && kind == EM_TX_STATUS05 && a->status == EM_TX_STATUS05
                    && a->transmit_epoch == a->receive_epoch && !a->receiving && !a->shutdown
                    ? EM_TX_STATUS06 : 0;
    }
}
void em_arb_initialized(volatile struct em_arbitration *a, uint32_t session)
{
    if (a->boot_pending && session == a->session_epoch && !a->shutdown && !a->off) {
        a->boot_pending = 0;
        a->ready = 1;
    }
}
