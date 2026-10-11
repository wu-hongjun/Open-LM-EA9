/* Metadata qualification build. No homing, servo or motor-drive call.
 * SPDX-License-Identifier: MIT */
#include "board.h"
#include "clock.h"
#include "delay.h"
#include "emount.h"
#include "em_uart.h"
#include "em_eic.h"
#include "motor.h"
#include "lens_profile.h"

static void powerdown_signal(void) {
    uint32_t t0; int low = 0;
    delay_ms(50);
    em_uart_disable();
    t0 = millis();
    while ((uint32_t)(millis() - t0) < 500u) {
        delay_ms(1);
        low = em_pin_level(EM_PIN_BODY_VD) ? 0 : low + 1;
        if (low >= 2) break;
    }
    PORT->Group[0].OUTSET.reg = 1u << 23;
    for (;;) { __WFI(); }
}
int main(void) {
    struct em_focus_cmd ignored;
    board_init_pins();
    clock_init();
    delay_init();
    PORT->Group[0].OUTSET.reg = 1u << 16;
    /* Establish the reference's zero-duty idle bridge state, then release it.
     * No motor_drive, motor_brake, homing or servo code is linked. */
    motor_init();
    motor_release();
    if (!ea9_profile_load()) { for (;;) { __WFI(); } }
    em_set_park_handler(motor_release);
    em_set_powerdown_handler(powerdown_signal);
    em_init();
    for (;;) {
        em_poll();
        if (em_take_focus_cmd(&ignored)) em_set_in_motion(0);
    }
}
