#include "profile_runtime.h"
#include "profile_nvm.h"
#include "emount.h"
#include "emount_packets.h"
#include <string.h>

uint16_t em_startup_aperture_av=EM_APERTURE_NOW;
void profile_apply_record(const uint8_t *r) {
    /* Only optical metadata changes. Motion/identity/timing remain the working baseline. */
    em_focal_mm10=pb_u16(r+12);
    em_startup_aperture_av=pb_u16(r+16);
    memcpy(em_msg_3F+7,r+104,64);
}
int profile_runtime_init(void) {
    const uint8_t *bank=(const uint8_t *)PB_BANK_ADDRESS;
    pb_setting active;
    int result=pb_boot(bank,(const uint8_t *)0x4000u,pb_samd21_io(),&active);
    if(result<0) return 0;
    /* PB_PENDING deliberately applies the old committed profile, not the failed request. */
    profile_apply_record(pb_profile(bank,active.slot));
    return 1;
}
