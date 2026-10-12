/* Production-main telemetry, captured frames and inherited coasting mechanics.
 * Each invocation has fresh globals. No camera/optical behavior is simulated. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main ea9_firmware_entry
#include "../src/main.c"
#undef main
#include "emount_packets.h"
struct host_pm host_pm;
extern void sim_reset(void),host_frame_sync(void);
extern double sim_pos,sim_vel;
extern uint32_t host_millis;
extern int sim_noise,sim_stop_lo,sim_stop_hi,sent_n,sent_overflow;
extern unsigned sim_clamp_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
extern int16_t sim_current_duty(void);
static uint32_t last_vd;
static unsigned auto_vd;
void em_uart_disable(void) {}
void vdd_init(void) {}
uint16_t vdd_read_mv(void) {return 3150;}
void vdd_read_burst(uint16_t *a,uint16_t *b,uint16_t t){(void)t;*a=*b=3150;}
void vdd_track_reset(void) {}
void vdd_track_result(uint16_t *a,uint16_t *b){*a=*b=3150;}
void vdd_track_sample(void) {
    if(auto_vd && (uint32_t)(host_millis-last_vd)>=17) {
        last_vd=host_millis;host_frame_sync();
    }
}
static int moving(void){return !(ea9_data[EA9_OFF_06+6]&0x80);}
static void frame(void) {host_frame_sync();focus_report();em_poll();}
static void check_frames(void) {
    assert(!sent_overflow);
    for(int i=0;i<sent_n;i++) {
        uint8_t *f=sent[i];unsigned n=sent_len[i],sum=0;
        assert(n>=9 && f[0]==0xf0 && f[n-1]==0x55);
        for(unsigned j=1;j<=n-4;j++)sum+=f[j];
        assert(f[n-3]==(sum&255) && f[n-2]==(sum>>8));
#ifndef EA9_FROZEN27
        if(f[5]==6) assert(f[8]==f[26] && f[9]==f[27]);
#endif
    }
}
int main(int argc,char **argv) {
    assert(argc==2);const char *c=argv[1];sim_reset();sim_noise=0;
    sim_stop_lo=0;sim_stop_hi=5952;em_init();em_handshake_done=1;
    g_homed=1;abs_encoder_track_reset();last_vd=host_millis;
    if(!strcmp(c,"coast40") || !strcmp(c,"coast5952")) {
        auto_vd=1;frame();
        struct em_focus_cmd m={.op=EM_OP_MOVE,.target=focus_counts_to_em06(!strcmp(c,"coast40")?40:5952)};
        focus_exec(&m);auto_vd=0;
        double start=sim_pos,velocity=sim_vel;
        printf("%s position=%.3f velocity=%.3f moving=%d\n",c,sim_pos,sim_vel,moving());
        if(velocity<=0 || !moving()) {fprintf(stderr,"Coast reported at rest\n");return 1;}
        assert(!sim_current_duty() && !sim_clamp_n && !ea9_af_faulted(&g_af_state));
        int before=sent_n;frame();assert(sent_n==before+2);
        const uint8_t *f=sent[before+1];
        assert(sent_len[before+1]==50 && f[45]==EM_REC_MOVE && !(f[6]&0x80));
        assert(sent[before][28]&0x40); /* 0x05 also still reports movement. */
        for(unsigned i=0;i<100;i++) {
            (void)millis();
            if((uint32_t)(host_millis-last_vd)>=17) {last_vd=host_millis;frame();}
            else focus_report();
        }
        assert(sim_pos>start+4 && !moving() && !sim_clamp_n);
    } else if(!strcmp(c,"reverse-stop")) {
        focus_report_at(400);host_millis+=1;focus_report_at(408);
        assert(moving() && ea9_data[EA9_OFF_06+7]==2);
        /* New opposite destination cannot erase observed forward motion. */
#ifndef EA9_FACTORY_AF
        focus_pred_begin(&g_pred,408,0,host_millis);
#endif
        focus_report_at(412);assert(moving() && ea9_data[EA9_OFF_06+7]==2);
        host_millis+=1;focus_report_at(404);assert(moving() && ea9_data[EA9_OFF_06+7]==4);
        struct em_focus_cmd stop={.op=EM_OP_STOP};focus_exec(&stop);
        assert(moving() && ea9_data[EA9_OFF_06+7]==4);
        sim_pos=404;int before=sent_n;frame();
        assert(sent[before+1][45]==EM_REC_STOP && !(sent[before+1][6]&0x80));
    } else if(!strcmp(c,"gap-reset")) {
        focus_report_at(1000);host_millis+=1;focus_report_at(1040);
        host_millis+=100;frame();assert(moving() && !ea9_data[EA9_OFF_06+7]);
        for(unsigned i=0;i<7;i++)assert(!ea9_data[EA9_OFF_06+0x26+i]);
#ifndef EA9_FROZEN27
        focus_motion_reset(&g_motion);
#endif
        abs_encoder_track_reset();focus_report();assert(moving());
        last_vd=host_millis;
        for(unsigned i=0;i<50;i++) {
            host_millis++;
            if((uint32_t)(host_millis-last_vd)>=17){last_vd=host_millis;frame();}
            else focus_report();
        }
        assert(!moving());
    } else return 2;
    check_frames();printf("transmitted motion %s: passed\n",c);return 0;
}
