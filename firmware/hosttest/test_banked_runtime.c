#include "protocol_fixture.h"
#include "emount_packets.h"
#include "profile_runtime.h"
#include "profile_nvm.h"
const pb_io *pb_samd21_io(void) { return 0; } /* target boot entry is not invoked */
int main(int argc,char **argv) {
    CHECK(argc==3); uint8_t bank[PB_BANK_BYTES]; pb_bank parsed;
    FILE *f=fopen(argv[1],"rb"); CHECK(f);
    CHECK(fread(bank,1,sizeof(bank),f)==sizeof(bank)); fclose(f);
    CHECK(pb_validate_bank(bank,&parsed)==PB_OK);
    unsigned slot=(unsigned)strtoul(argv[2],0,10); CHECK(slot<parsed.count);
    const uint8_t *r=pb_profile(bank,(uint8_t)slot);
    profile_apply_record(r); em_init();
    CHECK(em_focal_mm10==pb_u16(r+12) && u16(em_msg_05+0x1e)==pb_u16(r+12));
    CHECK(u16(em_msg_05+6)==pb_u16(r+16) && u16(em_msg_1B+6)==pb_u16(r+16));
    CHECK(u16(em_msg_08+6)==4224 && u16(em_msg_08+8)==6400);
    uint8_t frame[64],payload[32]={0};
    uint16_t n=request(frame,0x3f,payload,0); host_body_frame(frame,n); em_poll(); reply(sent_n-1,2,0x3f);
    CHECK(!memcmp(sent[sent_n-1]+7,r+104,64));
    payload[0]=0; payload[1]=20; n=request(frame,0x1b,payload,2); host_body_frame(frame,n); em_poll();
    CHECK(u16(em_msg_05+6)==5120);
    memset(payload,0,sizeof(payload)); n=request(frame,1,payload,sizeof(payload)); host_body_frame(frame,n); em_poll();
    CHECK(u16(em_msg_05+6)==pb_u16(r+16));
    CHECK(!sent_overflow && host_baud==EM_BAUD && host_baud_changes==0);
    puts("Bank selection reached production focal/name/aperture packets and session reset at unchanged baud.");
}
