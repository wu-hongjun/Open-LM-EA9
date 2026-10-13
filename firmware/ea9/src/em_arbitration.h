/* Candidate exchange ownership based on recovered factory CS/VD interlocks.
 * Not the complete factory fourteen-phase scheduler. SPDX-License-Identifier: MIT */
#ifndef EM_ARBITRATION_H
#define EM_ARBITRATION_H
#include <stdint.h>
enum em_tx_kind { EM_TX_CONTROL, EM_TX_STATUS05 = 5, EM_TX_STATUS06 = 6, EM_TX_SHUTDOWN = 16 };
struct em_arbitration {
    uint32_t receive_epoch, transmit_epoch, session_epoch;
    uint8_t receiving, transmitting, status, boot_pending, ready, shutdown, off, sequence, capture, capture_clocked;
};
void em_arb_open(volatile struct em_arbitration *a);
void em_arb_close(volatile struct em_arbitration *a);
void em_arb_request(volatile struct em_arbitration *a, uint8_t id);
void em_arb_frame(volatile struct em_arbitration *a, uint8_t sequence, uint8_t control_pending);
uint8_t em_arb_begin(volatile struct em_arbitration *a, uint8_t kind, uint8_t wire_busy, uint8_t control_pending);
void em_arb_end(volatile struct em_arbitration *a, uint8_t kind, uint8_t sent);
void em_arb_initialized(volatile struct em_arbitration *a, uint32_t session);
#endif
