#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "emount.h"
#include "focus_pred.h"
#include "focus_map.h"
#include "focus_dist.h"
#include "startup_trace.h"
extern uint32_t host_millis;
extern int sent_n,sent_overflow,sent_cs_asserted[];
extern uint8_t sent[][256];
extern uint16_t sent_len[];
void host_body_frame(const uint8_t *,uint16_t);
void host_frame_sync(void);
int host_cs_released(void);
static struct focus_pred g_pred;
static int32_t g_last_reported;
static unsigned reads,writes,mask;
static uint8_t memory[1024];
uint32_t st_lock(void){unsigned k=mask;mask=1;return k;}
void st_unlock(uint32_t k){mask=k;}
int st_read_page(uint32_t a,uint8_t out[64]){
 assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));reads++;memcpy(out,memory+(a-ST_FLASH_BASE),64);return 1;
}
int st_write_page(uint32_t a,const uint8_t in[64]){
 assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));writes++;
 for(unsigned j=0;j<64;j++)assert(memory[a-ST_FLASH_BASE+j]==255);
 memcpy(memory+(a-ST_FLASH_BASE),in,64);return 1;
}
void st_fail(uint8_t reason){(void)reason;abort();}
#include "report.inc"
int main(int argc,char **argv){
 assert(argc==2);unsigned omitted=argv[1][0]=='1';memset(memory,255,sizeof memory);st_init();
 uint8_t init[11]={0xf0,11,0,2,0x20,0x0a,0,0,0,0,0x55};unsigned sum=0;
 for(unsigned i=1;i<8;i++)sum+=init[i];init[8]=sum;init[9]=sum>>8;
 em_init();host_body_frame(init,sizeof init);em_poll();assert(em_handshake_done);sent_n=0;
 uint32_t previous=0;uint16_t expected=EM_FRAME_PERIOD_DEFAULT,count=0,omitted_count=0;
 static const uint32_t times[]={0,1,10,20,30,31,50,80,100,130,200,UINT32_MAX-20,UINT32_MAX-10,0,10,40,71};
 for(unsigned k=0;k<sizeof times/sizeof *times;k++){
  if(k==4){count=65534;omitted_count=65534;em_frame_period_n=65534;}
  uint32_t now=times[k];if(previous){uint32_t dt=now-previous;if(dt>=EM_FRAME_PERIOD_MIN && dt<=EM_FRAME_PERIOD_MAX){expected=dt;count++;}}
  previous=now;host_millis=now;host_frame_sync();assert(em_frame_period_ms==expected);
  assert(em_frame_period_n==(omitted?omitted_count:count));
  focus_pred_begin(&g_pred,4000,0,now-5);focus_pred_sample(&g_pred,3960,now);focus_report_at(3960);
  unsigned before=sent_n;em_poll();assert(sent_n==(int)before+2 && host_cs_released());
  uint8_t *status=sent[before+1];int32_t forecast=3960-8*(int32_t)expected;
  assert(status[5]==6 && (status[8]|status[9]<<8)==focus_counts_to_em06(forecast));
  assert((status[0x1a]|status[0x1b]<<8)==focus_counts_to_em06(3960) && !(status[6]&0x80));
  printf("PERIOD %u FORECAST %d\n",expected,forecast);
 }
 assert(!mask && !sent_overflow && writes==0 && reads==16);
 unsigned old_reads=reads;st_flush(0,host_millis,123,0,0,7);assert(!writes && reads==old_reads);
 st_flush(1,host_millis,123,0,0,7);assert(writes>=10 && writes<=13 && writes==1u+(memory[46]+3u)/4u && reads==16+writes && !mask);
 for(int k=0;k<sent_n;k++){
  assert(sent_cs_asserted[k]);unsigned n=sent_len[k],checksum=0;
  assert(sent[k][0]==0xf0 && sent[k][1]==n && sent[k][n-1]==0x55);
  for(unsigned i=1;i<n-3;i++)checksum+=sent[k][i];assert(sent[k][n-3]==(checksum&255) && sent[k][n-2]==(checksum>>8));
  printf("WIRE %u:",n);for(unsigned i=0;i<n;i++)printf("%02x",sent[k][i]);putchar('\n');
 }
 for(unsigned k=0;k<writes;k++){
  uint8_t *p=memory+64*k;assert(!memcmp(p,"E9S2",4));uint32_t crc=p[60]|(uint32_t)p[61]<<8|(uint32_t)p[62]<<16|(uint32_t)p[63]<<24;
  assert(crc==st_crc32(p,60));printf("TRACE %u:",k);for(unsigned i=0;i<64;i++)printf("%02x",p[i]);putchar('\n');
 }
 printf("PASS samples=17 frames=%d tracePages=%u reads=%u writes=%u\n",sent_n,writes,reads,writes);return 0;
}
