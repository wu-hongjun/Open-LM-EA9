#include <assert.h>
#include <setjmp.h>
#include <stdio.h>
#include <string.h>
#include "board.h"
#include "delay.h"
#include "em_uart.h"
#include "emount.h"
#include "startup_trace.c"
struct host_wdt wdt;
struct host_gclk gclk;
struct host_pm pm;
static jmp_buf halted;
static unsigned char flash[1024];
static unsigned writes,masked,releases;
extern uint32_t host_millis,host_cs_rise_ms;
extern int host_wait_mode,host_vd_after_ms;
uint32_t st_lock(void){return 0;}
void st_unlock(uint32_t k){(void)k;}
void host_disable_irq(void){masked++;}
void host_wfi(void){longjmp(halted,1);}
void motor_emergency_release(void){releases++;}
int st_read_page(uint32_t a,uint8_t *p){assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));memcpy(p,flash+(a-ST_FLASH_BASE),64);return 1;}
int st_write_page(uint32_t a,const uint8_t *p){assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));for(unsigned k=0;k<64;k++)assert(flash[a-ST_FLASH_BASE+k]==255);memcpy(flash+(a-ST_FLASH_BASE),p,64);writes++;return 1;}
#include "terminal.inc"
static int boot(void){memset(&wdt,0,sizeof wdt);pm.RCAUSE.reg=1;host_millis=0;if(setjmp(halted))return 1;st_crash_boot();return 0;}
static void events32(void){for(unsigned i=0;i<32;i++)st_note(ST_HANDSHAKE,0,0,0,0,0,i);}
static void shut(void){events32();st_flush(1,2355,0,0,0,0);st_terminal(ST_VD_TIMEOUT,0,2856);st_terminal(ST_PA23,0,2856);}
int main(int argc,char **argv){assert(argc==2);memset(flash,255,sizeof flash);const char *mode=argv[1];
 if(!strcmp(mode,"clean16")||!strcmp(mode,"availability")){
  for(unsigned n=0;n<16;n++){assert(!boot());assert(writes==n+1);}
  if(!strcmp(mode,"availability")){if(boot()){puts("FAIL availability: clean POR boot 17 never returns from st_crash_boot; 16 clean baseline pages, no crash");return 23;}return 0;}
  assert(boot());assert(writes==16);assert(masked==1 && releases==17);assert(!crash_latched && !wdt.CTRL.reg);
  puts("PASS clean POR boots 1..16 return; boot17 halts before board/protocol; no crash latch, no WDT");
 }else if(!strcmp(mode,"fulltail")){
  for(unsigned i=0;i<16;i++){
   struct page p={.magic={'E','9','S','3'},.version=3,.type=5,.cohort=i+1,.n=1,.slot=i,.reserved=1};
   p.crc=st_crc32((const uint8_t *)&p,60);memcpy(flash+i*64,&p,64);
  }
  assert(boot());assert(!writes && !crash_latched && !wdt.CTRL.reg);
  puts("PASS initially full valid POR-only tail refuses first boot with zero writes");
 }else if(!strcmp(mode,"crash-latch")){
  pm.RCAUSE.reg=32;if(!setjmp(halted)){st_crash_boot();assert(!"crash boot returned");}
  assert(writes==1);assert(boot());assert(writes==1 && crash_latched);
  puts("PASS WDT-cause record still latches subsequent POR without new writes");
 }else if(!strcmp(mode,"observed-shape")){
  for(unsigned n=0;n<4;n++)assert(!boot());shut();assert(writes==14);
  assert(!boot());assert(writes==15);st_summary(ST_STAGE,ST_WAIT_RISE,8000);
  host_millis=8000;if(!setjmp(halted))st_fail(ST_CS_RISE_WAIT);
  assert(writes==16 && flash[15*64+5]==1 && s.fault==8 && s.stage==8 && !s.planned && !s.motion_chunks);
  assert(boot());assert(writes==16 && !crash_latched);
  puts("PASS synthetic observed page shape: four boots + summary/motion/events/two footers -> 14; boot -> 15; stage8 fault -> 16; next boot halted");
 }else if(!strcmp(mode,"stage8")){
  assert(!boot());st_watchdog_start();assert(!wdt.CTRL.reg);
  host_wait_mode=1;host_cs_rise_ms=0;host_vd_after_ms=-1;
  if(!setjmp(halted)){em_init();assert(!"silent-CS em_init returned");}
  assert(host_millis==8000 && s.stage==8 && s.fault==8 && !s.connected && !s.rx_count && !s.tx_count);
  assert(!wdt.CTRL.reg && !retained.magic && writes==7);
  puts("PASS actual em_init -> st_fail at 8000 synthetic ticks, stage8, no handshake, watchdog disabled, no retained checkpoint, 7 pages");
 }else if(!strcmp(mode,"healthy-shutdown")){
  assert(!boot());shut();assert(writes==14);st_terminal(ST_TAIL_DONE,0,2956);assert(writes==15);
  assert(!boot());assert(writes==16);assert(boot());
  puts("PASS clean terminal trace workload -> 15 pages; next boot consumes last page; subsequent clean boot halts; physical shutdown not modeled");
 }else assert(0);
 return 0;
}
