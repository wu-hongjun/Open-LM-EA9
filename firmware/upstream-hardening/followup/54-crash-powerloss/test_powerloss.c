#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
static jmp_buf checkpoint_jump;
static unsigned interrupt_step,seen_step;
static void checkpoint_step(void){if(interrupt_step && ++seen_step==interrupt_step)longjmp(checkpoint_jump,1);}
#include "startup_trace.c"
static unsigned char flash[1024],motion[144];
static unsigned writes,reads,cut=64;
static int read_fail;
uint32_t st_lock(void){return 0;}
void st_unlock(uint32_t k){(void)k;}
const uint8_t *st_motion_data(void){return motion;}
int st_read_page(uint32_t a,uint8_t *p){assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));reads++;if(read_fail)return 0;memcpy(p,flash+(a-ST_FLASH_BASE),64);return 1;}
int st_write_page(uint32_t a,const uint8_t *p){assert(a>=ST_FLASH_BASE && a<=ST_FLASH_END-64 && !(a&63));unsigned char *d=flash+(a-ST_FLASH_BASE);for(unsigned i=0;i<64;i++)assert(d[i]==255);writes++;memcpy(d,p,cut);return cut==64;}
static void fresh(void){memset(flash,255,1024);memset(&retained,0,sizeof retained);writes=reads=read_fail=0;cut=64;st_init();}
static void sample(void){st_summary(ST_STAGE,ST_LOOP,0);st_summary(ST_RX,0x91,17);st_record(18,ST_FAULT|(11u<<8),0);st_checkpoint(123456);}
static void dump(const char *dir,unsigned n){char path[4096];snprintf(path,sizeof path,"%s/tail-%03u.bin",dir,n);FILE *f=fopen(path,"wb");assert(f);assert(fwrite(flash,1,1024,f)==1024);assert(!fclose(f));}
int main(int argc,char **argv){assert(argc==2);const char *dir=argv[1];
/* Interrupt the real checkpoint after each mutation/publication boundary. */
for(unsigned step=1;step<=5;step++){fresh();sample();s.stage=ST_REFERENCE;interrupt_step=step;seen_step=0;if(!setjmp(checkpoint_jump))st_checkpoint(999);interrupt_step=0;st_init();st_boot_record(32);assert(flash[10]==(step==5));if(step==5)assert(flash[36]==ST_REFERENCE);}
/* Every exact reset register value: eligibility is exact WDT or SYST. */
for(unsigned cause=0;cause<256;cause++){fresh();sample();st_init();assert(st_boot_record(cause)==((cause&96)!=0));assert(writes==1);assert(flash[5]==5 && flash[7]==1 && flash[11]==cause);assert(flash[10]==(cause==32 || cause==64));if(flash[10])assert(!memcmp(flash+12,&retained.summary,48));else for(unsigned i=12;i<60;i++)assert(!flash[i]);assert(retained.magic==0);}
/* One flipped bit anywhere in retained marker, CRC, payload must not recover. */
for(unsigned b=0;b<sizeof retained*8;b++){fresh();sample();((unsigned char *)&retained)[b/8]^=1u<<(b%8);st_init();st_boot_record(32);assert(flash[10]==0);}
/* Stale checkpoint after cold/external reset cannot resurrect on warm reset. */
for(unsigned c=1;c<=16;c*=2){fresh();sample();st_init();st_boot_record(c);st_init();st_boot_record(32);assert(flash[74]==0);}
/* All byte-prefix power cuts; no retry within boot, no RAM replay next boot. */
for(unsigned n=0;n<=64;n++){fresh();sample();st_init();cut=n;st_boot_record(32);assert(writes==1);dump(dir,n);st_boot_record(32);assert(writes==(n==64?2:1));assert(retained.magic==0);if(n<64){cut=64;st_init();unsigned slot=n?1:0;int halt=st_boot_record(1);assert(halt==(n!=0));assert(writes==(n?1u:2u));if(!n)assert(flash[64*slot+10]==0);}}
/* Durable crash latch survives later cold boots and prevents tail exhaustion. */
for(unsigned cause=0;cause<256;cause++){fresh();sample();assert(st_boot_record(32)==1);unsigned before=writes;st_init();assert(st_boot_record(cause)==1);assert(writes==before && retained.magic==0);}
/* Corrupt occupied pages fail closed as storage damage, not proof of crash. */
for(unsigned bit=0;bit<512;bit++){fresh();sample();st_boot_record(32);flash[bit/8]^=1u<<(bit%8);st_init();assert(st_boot_record(1)==1);assert(writes==1);}
/* CRC-valid foreign/malformed headers are occupied, not a storage-CRC latch. */
const unsigned offsets[]={0,4,5,6,7,8,9,10,11};
const unsigned values[]={'X',4,6,2,2,1,1,2,0};
for(unsigned i=0;i<9;i++){fresh();sample();st_boot_record(32);flash[offsets[i]]=values[i];uint32_t crc=st_crc32(flash,60);memcpy(flash+60,&crc,4);st_init();assert(st_boot_record(1)==0);assert(writes==2 && flash[70]==2 && flash[74]==0);dump(dir,970+i);}
/* Full tail, holes before occupied frontier, foreign/torn records. */
for(unsigned last=0;last<16;last++){fresh();struct page old={.magic={'E','9','S','3'},.version=3,.type=5,.cohort=last+1,.n=1,.slot=last,.reserved=1};old.crc=st_crc32((const uint8_t *)&old,60);memcpy(flash+last*64,&old,64);st_init();sample();assert(st_boot_record(32)==1);assert(writes==(last==15?0:1));if(last<15)assert(flash[(last+1)*64+5]==5);for(unsigned i=0;i<last;i++)for(unsigned k=0;k<64;k++)assert(flash[i*64+k]==255);}
fresh();sample();read_fail=1;st_init();assert(st_boot_record(1)==1);assert(writes==0 && retained.magic==0);
/* Actual baseline plus subsequent ordinary snapshot, with separate cohort. */
fresh();assert(st_boot_record(1)==0);sample();st_flush(1,123456,1,0,0,255);assert(flash[6]==1 && flash[70]==2);dump(dir,998);
/* A complete emitted record for independent CRC/decoder and corruption tests. */
fresh();sample();st_init();st_boot_record(32);dump(dir,999);
printf("PASS exact-reset=256 retained-bit-corruption=%zu torn-prefix=65 frontier=16 stale-reset=5 read-failure=1 checkpoint-interrupt=5 persisted-latch=256 corrupt-storage=512\n",sizeof retained*8);
return 0;}
