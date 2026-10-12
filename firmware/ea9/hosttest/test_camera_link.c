/* Compose production handshake, reference and shutdown routines with frames.
 * The peripheral/mechanical shims do not model a camera, IRQ timing or optics. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main ea9_firmware_entry
#include "../src/main.c"
#undef main
#include "emount_packets.h"
struct host_pm host_pm;
extern void sim_reset(void), host_body_frame(const uint8_t *, uint16_t), host_frame_sync(void);
extern void host_window_payload(const uint8_t *, uint16_t);
extern uint32_t host_millis;
extern int sim_noise, sim_stop_lo, sim_stop_hi, sent_n, host_tx_fail_id, host_vd_reads;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int16_t sim_current_duty(void);
static unsigned disabled;
void em_uart_disable(void) { ++disabled; }
void vdd_init(void) {}
uint16_t vdd_read_mv(void) { return 3150; }
void vdd_read_burst(uint16_t *lo,uint16_t *hi,uint16_t ms) { (void)ms; *lo=*hi=3150; }
void vdd_track_reset(void) {}
void vdd_track_result(uint16_t *lo,uint16_t *hi) { *lo=*hi=3150; }
void vdd_track_sample(void) {}
static void request(uint8_t id,uint8_t sequence) {
    uint8_t b[11]={0xf0,11,0,2,sequence,id,0,0,0,0,0x55};
    uint16_t sum=0;for(unsigned i=1;i<8;i++)sum+=b[i];
    b[8]=(uint8_t)sum;b[9]=(uint8_t)(sum>>8);
    host_body_frame(b,sizeof b); focus_report(); em_poll();
}
static int fail(const char *reason) { fprintf(stderr,"%s\n",reason);return 1; }
int main(int argc,char **argv) {
    assert(argc==3); const char *scenario=argv[1];
    uint8_t profile[256];FILE *f=fopen(argv[2],"rb");assert(f);
    assert(!fseek(f,-256,SEEK_END) && fread(profile,1,256,f)==256);fclose(f);
    assert(ea9_profile_load_from(profile));
    sim_reset();sim_noise=0;sim_stop_lo=0;sim_stop_hi=5952;
    em_set_park_handler(park_to_infinity);em_set_powerdown_handler(powerdown_signal);
    em_init();assert(!g_homed && !em_handshake_done);
    if(!strcmp(scenario,"fault-home"))ea9_io_trip(EA9_IO_ADC);
    const uint8_t ids[]={1,7,0x0b,8,9,0x0d,0x10,0x0a};
    for(unsigned i=0;i<sizeof ids;i++) {
        if(i==sizeof(ids)-1 && !strcmp(scenario,"fail-init"))host_tx_fail_id=0x0a;
        request(ids[i],(uint8_t)i);
        if(i<sizeof(ids)-1)assert(!em_handshake_done);
    }
    if(!strcmp(scenario,"fail-init")) {
        if(em_handshake_done)return fail("failed final init armed handshake");
        assert(!g_homed && !disabled);puts("failed initialization remains unarmed: passed");return 0;
    }
    assert(em_handshake_done && !g_homed);
    if(!strcmp(scenario,"restart-init")) {
        request(1,0x51);
        if(em_handshake_done)return fail("new initializer retained old status handshake");
        int before=sent_n;host_frame_sync();em_poll();assert(sent_n==before);
        for(unsigned i=1;i<sizeof ids;i++)request(ids[i],(uint8_t)(0x51+i));
        assert(em_handshake_done && !g_homed);
        puts("new initializer gates status until final reply: passed");return 0;
    }
    motor_home();
    if(!strcmp(scenario,"fault-home"))assert(!g_homed && ea9_af_faulted(&g_af_state));
    else assert(g_homed && !ea9_af_faulted(&g_af_state));
    if(!strcmp(scenario,"fault-idle"))ea9_io_trip(EA9_IO_ADC);
    if(!strcmp(scenario,"fail-tail")) {
        em_post_event(EM_REC_MOVE,1);em_post_query_answer(EM_REC_Q_POS2D,0x1234);
        host_tx_fail_id=6;host_frame_sync();focus_report();em_poll();
        if(em_events_sent)return fail("unsent event tail consumed");
        host_tx_fail_id=-1;int before=sent_n;
        host_frame_sync();focus_report();em_poll();
        assert(sent_n==before+2 && sent_len[before+1]==53);
        assert(sent[before+1][45]==EM_REC_MOVE && sent[before+1][47]==EM_REC_Q_POS2D);
        puts("failed status preserves event/query tail: passed");return 0;
    }
    /* Query/status reception still proceeds with motion inhibited. */
    host_frame_sync();focus_report();em_poll();
    if(!strcmp(scenario,"fail-shutdown"))host_tx_fail_id=0x16;
    int before=sent_n, vd_before=host_vd_reads;request(0x16,0x71);
    if(!strcmp(scenario,"fail-shutdown")) {
        if(em_shutdown_acked || disabled)return fail("failed shutdown falsely acknowledged");
        assert(sent_n==before);puts("failed shutdown does not power down bus: passed");return 0;
    }
    assert(em_shutdown_acked && disabled==1 && g_af_state.shutdown);
    if(host_vd_reads-vd_before<2)return fail("motion fault skipped shutdown VD wait");
    assert(sent_n==before+1 && sent[before][5]==0x16 && !sim_current_duty());
    before=sent_n;host_frame_sync();em_poll();assert(sent_n==before);
    request(0x16,0x72);assert(disabled==1); /* Echo may be suppressed by real disabled UART. */
    for(int i=0;i<sent_n;i++) {
        uint8_t *b=sent[i];uint16_t n=sent_len[i],sum=0;
        for(unsigned j=1;j<=n-4;j++)sum+=b[j];
        assert(b[0]==0xf0 && b[n-1]==0x55 && b[n-3]==(sum&255) && b[n-2]==(sum>>8));
    }
    printf("composed startup/reference/shutdown %s: passed\n",scenario);return 0;
}
