/* Regression for Stop FIFO pressure and repeated absolute wire targets.
 * Mechanical simulator only; each scenario has fresh production globals. */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main ea9_firmware_entry
#include "../src/main.c"
#undef main
#include "emount_packets.h"
struct host_pm host_pm;
extern void sim_reset(void);
extern double sim_pos;
extern int sim_noise,sim_stop_lo,sim_stop_hi;
extern unsigned sim_clamp_n;
extern int16_t sim_current_duty(void);
extern uint32_t host_millis;
extern void host_frame_sync(void);
extern void host_body_frame(const uint8_t*,uint16_t);
extern int sent_n;
extern uint8_t sent[][256];
extern uint16_t sent_len[];
static int repeats,last_repeat;
void em_uart_disable(void) {}
void vdd_init(void) {}
uint16_t vdd_read_mv(void) { return 3150; }
void vdd_read_burst(uint16_t *lo,uint16_t *hi,uint16_t ms) {(void)ms;*lo=*hi=3150;}
void vdd_track_reset(void) {}
void vdd_track_result(uint16_t *lo,uint16_t *hi) {*lo=*hi=3150;}
static void seal(uint8_t *f,unsigned n) {
 unsigned sum=0; f[1]=n; f[2]=n>>8;
 for(unsigned i=1;i<=n-4;i++)sum+=f[i];
 f[n-3]=sum;f[n-2]=sum>>8;f[n-1]=0x55;
}
static void move(unsigned target) {
 uint8_t f[27]={0xf0,0,0,1,0,4}; f[19]=EM_REC_MOVE;
 f[20]=target; f[21]=target>>8; seal(f,sizeof f);host_body_frame(f,sizeof f);
}
void vdd_track_sample(void) {
 if(repeats && host_millis-last_repeat>=16) {
  last_repeat=host_millis; move(focus_counts_to_em06(5952));
 }
}
int main(int argc,char **argv) {
 assert(argc==2);sim_reset();sim_noise=0;sim_stop_lo=0;sim_stop_hi=5952;
 em_init();g_homed=1;abs_encoder_track_reset();
 if(!strncmp(argv[1],"stop-",5)) {
  em_handshake_done=1;
  struct em_focus_cmd tiny={.op=EM_OP_MOVE,.target=focus_counts_to_em06(4)};
  focus_exec(&tiny);focus_exec(&tiny);
  assert(g_focus_moves==2 && !ea9_af_faulted(&g_af_state));
  struct em_focus_cmd stop={.op=EM_OP_STOP};focus_exec(&stop);
  if(!strcmp(argv[1],"stop-coalesce")) {focus_exec(&stop);focus_exec(&stop);}
  if(!strcmp(argv[1],"stop-pending")) focus_exec(&tiny);
  if(!strcmp(argv[1],"stop-reordered")) {
   int before=sent_n;host_frame_sync();em_poll();
   assert(sent_n==before+2 && sent[before+1][45]==EM_REC_MOVE);
   /* Now [Stop], then [Stop, Move], then a newer Stop. */
   focus_exec(&tiny);focus_exec(&stop);
  }
  unsigned found=0,events=0;
  for(unsigned i=0;i<3;i++) {
   int before=sent_n;host_frame_sync();em_poll();
   assert(sent_n==before+2);
   const uint8_t *f=sent[before+1];
   if(sent_len[before+1]>48) {
    if(f[45]!=(events ? EM_REC_STOP : EM_REC_MOVE)) {
     fprintf(stderr,"Stop acknowledgement/order lost: event=%u code=0x%02x\n",events,f[45]);return 1;
    }
    events++;found+=f[45]==EM_REC_STOP;
   }
  }
  printf("%s idle_stops=%u transmitted_events=%u transmitted_stop_ack=%u\n",argv[1],g_stops_idle,events,found);
  if(events!=2 || found!=1) return 1;
 } else if(!strcmp(argv[1],"repeat") || !strcmp(argv[1],"single")) {
  repeats=!strcmp(argv[1],"repeat");last_repeat=host_millis;
  struct em_focus_cmd m={.op=EM_OP_MOVE,.target=focus_counts_to_em06(5952)};
  focus_exec(&m);
  printf("%s fault=%u elapsed_ms=%u position=%.3f retargets=%u outcome=%u stop_contacts=%u duty=%d\n",argv[1],g_af_state.fault_reason,host_millis,sim_pos,g_focus_ring[0].retargets,g_focus_ring[0].outcome,sim_clamp_n,sim_current_duty());
  assert(!sim_clamp_n && sim_current_duty()==0);
  if(g_af_state.fault_reason || g_focus_ring[0].retargets || g_focus_ring[0].outcome!=SERVO_DEADLINE) {
   fprintf(stderr,"Repeated target faulted/restarted\n");return 1;
  }
 } else return 2;
 return 0;
}
