/* Production foreground home service under supplied mechanical/link events. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main ea9_firmware_entry
#include "../src/main.c"
#undef main
struct host_pm host_pm;
extern void sim_reset(void),host_body_frame(const uint8_t *,uint16_t);
extern int sim_noise,sim_stop_lo,sim_stop_hi;
extern double sim_pos;
extern uint32_t host_millis;
extern int16_t sim_current_duty(void);
extern int sent_n;
extern void host_frame_sync(void);
extern uint8_t sent[][256];
static const char *scenario;
static unsigned samples,disabled;
static void seal(uint8_t *f,unsigned n) {unsigned sum=0;for(unsigned i=1;i<n-3;++i)sum+=f[i];f[n-3]=sum;f[n-2]=sum>>8;f[n-1]=0x55;}
static void stop(void) {uint8_t f[23]={0xf0,23,0,1,0,4};f[19]=EM_REC_STOP;seal(f,sizeof f);host_body_frame(f,sizeof f);}
static void move(void) {uint8_t f[27]={0xf0,27,0,1,0,4};uint16_t t=focus_counts_to_em06(400);f[19]=EM_REC_MOVE;f[20]=t;f[21]=t>>8;seal(f,sizeof f);host_body_frame(f,sizeof f);}
static void request(uint8_t id) {uint8_t f[11]={0xf0,11,0,2,0x71,id,0,0,0,0,0x55};seal(f,sizeof f);host_body_frame(f,sizeof f);}
void em_uart_disable(void) {++disabled;}
void vdd_init(void) {}
uint16_t vdd_read_mv(void) {return 3150;}
void vdd_read_burst(uint16_t *lo,uint16_t *hi,uint16_t ms) {(void)ms;*lo=*hi=3150;}
void vdd_track_reset(void) {}
void vdd_track_result(uint16_t *lo,uint16_t *hi) {*lo=*hi=3150;}
void vdd_track_sample(void) {
    ++samples;
    if(samples==4) {
        assert(sim_pos<1000);
        if(!strcmp(scenario,"shutdown"))request(0x16);
        else if(!strcmp(scenario,"fault"))ea9_io_trip(EA9_IO_ADC);
        else if(!strcmp(scenario,"capture"))request(0x0a);
        else if(!strcmp(scenario,"session-reset"))request(1);
        else if(strcmp(scenario,"stop-before-home"))stop();
    }
    if(!strcmp(scenario,"budget") && samples==8)stop();
}
static void service(void) {
    host_frame_sync(); /* Supplied cadence event; no physical IRQ timing claim. */
    em_poll();
#ifndef EA9_FROZEN29
    home_service();
#else
    focus_service(); /* Frozen main consumed its only homing attempt. */
#endif
}
int main(int argc,char **argv) {
    assert(argc==3);scenario=argv[1];uint8_t profile[256];FILE *f=fopen(argv[2],"rb");assert(f);
    assert(!fseek(f,-256,SEEK_END)&&fread(profile,1,256,f)==256);fclose(f);assert(ea9_profile_load_from(profile));
    sim_reset();sim_noise=0;sim_stop_lo=0;sim_stop_hi=5952;sim_pos=1000;
    em_init();em_set_powerdown_handler(powerdown_signal);
    request(1);em_poll();request(0x0a);em_poll();assert(em_handshake_done);
    if(!strcmp(scenario,"stop-before-home"))stop();
#ifdef EA9_FROZEN29
    motor_home();
#else
    for(unsigned i=0;i<1000;++i) {
        service();
        if(g_reference.phase!=EA9_HOME_DRIVING && g_reference.phase!=EA9_HOME_SETTLING)break;
    }
#endif
    if(!strcmp(scenario,"capture")) {
        assert(g_homed && !ea9_af_faulted(&g_af_state));
#ifndef EA9_FROZEN29
        assert(g_home_attempts==1);
#endif
    } else if(!strcmp(scenario,"shutdown")) {
        service();assert(disabled==1 && em_shutdown_acked && g_af_state.shutdown && !sim_current_duty());
    } else {
        assert(!g_homed && !sim_current_duty());
        unsigned before_samples=samples;
        for(unsigned i=0;i<10;++i)service(); /* No unsolicited retry. */
        assert(samples==before_samples);
        if(!strcmp(scenario,"session-reset")) {
            assert(!em_handshake_done);request(0x0a);em_poll();assert(em_handshake_done);
        }
        move();service();
        for(unsigned i=0;i<1000;++i) {
            if(g_reference.phase!=EA9_HOME_DRIVING && g_reference.phase!=EA9_HOME_SETTLING)break;
            service();
        }
        if(!strcmp(scenario,"resume") || !strcmp(scenario,"stop-before-home") || !strcmp(scenario,"session-reset")) {
            if(!g_homed) {fputs("cancelled reference stayed permanently unready\n",stderr);return 1;}
            assert(!ea9_af_faulted(&g_af_state) && g_next_pending);
        } else if(!strcmp(scenario,"budget")) {
            assert(!g_homed);move();for(unsigned i=0;i<10;++i)service();
            assert(!g_homed && !sim_current_duty());
#ifndef EA9_FROZEN29
            assert(g_home_attempts==2);
#endif
        } else if(!strcmp(scenario,"fault"))assert(!g_homed && ea9_af_faulted(&g_af_state));
        else return 2;
        request(0x16);em_poll();assert(em_shutdown_acked && disabled==1 && !sim_current_duty());
    }
    printf("home readiness %s passed\n",scenario);return 0;
}
