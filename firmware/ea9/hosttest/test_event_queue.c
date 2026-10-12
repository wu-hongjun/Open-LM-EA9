/* Enumerate all Move/Stop sequences through length eight, then check the
 * actual transmitted tails. This specifies our bounded overflow policy. */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#ifndef EA9_EMOUNT_PROBE_SOURCE
#define EA9_EMOUNT_PROBE_SOURCE "../src/emount.c"
#endif
#include EA9_EMOUNT_PROBE_SOURCE
extern void host_frame_sync(void);
extern unsigned char sent[][256];
extern unsigned short sent_len[];
extern int sent_n, sent_overflow;
int main(void) {
 em_init(); em_handshake_done=1; unsigned cases=0;
 for(unsigned n=1;n<=8;n++) for(unsigned bits=0;bits<(1u<<n);bits++) {
  g_event_n=0;sent_n=sent_overflow=0;
  unsigned stops=0;
  for(unsigned i=0;i<n;i++) {
   unsigned code=(bits&(1u<<i))?EM_REC_STOP:EM_REC_MOVE;
   stops+=code==EM_REC_STOP;em_post_event(code,code==EM_REC_STOP?1:0);
   assert(g_event_n<=2);
  }
  unsigned found=0,events=0,last=0;
  for(unsigned f=0;f<3;f++) {
   int before=sent_n; host_frame_sync();em_poll();assert(sent_n==before+2);
   if(sent_len[before+1]>48) {
    assert(sent_len[before+1]==50);last=sent[before+1][45];
    found+=last==EM_REC_STOP;events++;
   }
  }
  if(found!=(stops?1u:0u) || (bits&(1u<<(n-1)) && last!=EM_REC_STOP)) {
   printf("queue property FAILED length=%u sequence=%u stops=%u found=%u last=0x%x\n",n,bits,stops,found,last);return 1;
  }
  assert(events<=2 && !g_event_n && !sent_overflow);cases++;
 }
 printf("queue properties passed: %u event sequences, bounded depth, Stop retained and newest Stop emitted last\n",cases);return 0;
}
