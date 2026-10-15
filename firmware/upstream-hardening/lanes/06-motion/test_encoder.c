#include <stdint.h>
#include <limits.h>
#include <stdlib.h>
#include <stdio.h>
#define ENC_COUNTS 16384
static int32_t g_track;
static uint16_t g_track_last,raw;
static int latch;
static uint16_t abs_encoder_raw(void) {return raw;}
void motor_inhibit(void) {latch=1;}
#include "encoder_test.inc"
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    int which=atoi(argv[1]);
    if(which==0) {g_track=INT32_MAX;raw=1;}
    if(which==1) {g_track=INT32_MIN;g_track_last=1;}
    if(which==2) {g_track_last=16380;raw=4;}
    if(which==3) {g_track_last=4;raw=16380;}
    int32_t result=abs_encoder_track();
    int good=which<2?latch && result==(which==0?INT32_MAX:INT32_MIN):!latch && result==(which==2?8:-8);
    printf("%s result=%d inhibit=%d\n",good?"PASS":"FAIL",result,latch);return !good;
}
