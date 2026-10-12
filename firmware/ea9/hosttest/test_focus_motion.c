/* Pure observer contracts; synthetic positions/clocks/VD, no motor model. */
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "focus_motion.h"
static struct focus_motion s;
static int8_t take(int32_t p, uint32_t t, uint32_t f) {
    return focus_motion_sample(&s, p, t, f, 17);
}
int main(int argc, char **argv) {
    assert(argc == 2); focus_motion_reset(&s);
    const char *c = argv[1];
    if (!strcmp(c,"coast")) {
        assert(take(200,0,0)==-1 && !s.known);
        take(204,1,0); assert(s.known && s.moving && s.direction==1);
        take(208,2,0); assert(take(208,17,1)==0 && !s.delta && s.moving);
        assert(take(208,34,2)==1 && s.known && !s.moving && !s.direction);
    } else if (!strcmp(c,"slow")) {
        take(500,0,0);
        for (int i=1;i<=3;i++) {take(500+i,i,0);assert(!s.known);}
        take(504,4,0); assert(s.known && s.moving && s.direction==1);
    } else if (!strcmp(c,"reversal")) {
        take(200,0,0);take(208,1,0); assert(s.direction==1);
        take(204,2,0); assert(s.direction==-1 && s.moving);
        take(200,3,0);take(200,17,1);
        assert(s.moving && s.delta==0); /* Net-zero path was observed moving. */
        take(200,34,2);assert(s.known && !s.moving);
    } else if (!strcmp(c,"stale")) {
        take(200,0,0);take(204,1,0);
        assert(take(204,20,1)==-1 && !s.known && !s.direction && !s.delta);
        for(int i=0;i<20;i++) take(204,20,1);
        assert(!s.known); /* Same timestamp never establishes rest. */
        assert(take(204,37,2)==0 && !s.delta);assert(s.known && !s.moving);
    } else if (!strcmp(c,"vd-gap")) {
        take(200,0,0);take(204,16,0);
        assert(take(204,17,2)==-1 && !s.known && !s.delta);
        assert(take(204,34,3)==0 && !s.delta);assert(s.known && !s.moving);
    } else if (!strcmp(c,"no-vd")) {
        take(200,0,0);
        for(int t=1;t<=35;t++) take(200,t,0);
        assert(!s.known);take(200,36,1);assert(!s.known);
        for(int t=37;t<52;t++)take(200,t,1);
        take(200,52,2);assert(s.known && !s.moving);
    } else if (!strcmp(c,"wrap")) {
        uint32_t t=UINT32_MAX-8;
        take(200,t,UINT32_MAX);take(204,t+1,UINT32_MAX);
        assert(take(204,t+17,0)==0 && s.moving && !s.delta);
        take(204,t+34,1);assert(s.known && !s.moving);
    } else if (!strcmp(c,"limits")) {
        take(5952,0,0);take(5956,1,0);assert(s.moving && s.direction==1);
        focus_motion_reset(&s);take(-4,0,0);take(-1,1,0);assert(!s.known);
        take(0,2,0);assert(s.moving && s.direction==1);
        take(-5,3,0);assert(s.moving && s.direction==-1 && s.motion_counts==-5);
    } else if (!strcmp(c,"reset")) {
        take(2000,0,100);take(2040,1,100);assert(s.moving);
        focus_motion_reset(&s);assert(take(0,2,101)==-1 && !s.known && !s.delta);
        take(0,19,102);assert(s.known && !s.moving && !s.delta);
    } else if (!strcmp(c,"burst")) {
        take(200,0,0);
        for(int i=1;i<=40;i++)take(200,0,i);
        assert(!s.known);
        take(200,17,41);assert(s.known && !s.moving);
    } else if (!strcmp(c,"resume-history")) {
        take(0,0,1);
        for(int t=1;t<=17;t++)take(t*4,t,t==17?2:1);
        for(int t=18;t<=52;t++)take(t*4,t,2);
        assert(!s.known && !s.history_ready);
        assert(take(53*4,53,3)==0 && !s.delta); /* No partial one-ms velocity. */
        for(int t=54;t<70;t++)take(t*4,t,3);
        assert(take(70*4,70,4)==1 && s.delta==17);
    } else if (!strcmp(c,"sub-resolution-jitter")) {
        for(int anchor=0;anchor<=100;anchor+=100) {
            focus_motion_reset(&s);take(anchor,0,0);
            for(unsigned t=1;t<=102;t++)take(anchor+(t&1?1:-1),t,t/17);
            assert(s.known && !s.moving && !s.direction && !s.delta);
        }
    } else if (!strcmp(c,"slow-frames")) {
        take(400,0,0);
        for(unsigned t=1;t<=68;t++)take(400+t/17,t,t/17);
        assert(s.known && s.moving && s.direction==1 && s.motion_counts==404);
    } else return 2;
    printf("motion observer %s: passed\n",c);return 0;
}
