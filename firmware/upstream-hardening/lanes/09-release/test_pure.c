#include <stdint.h>
#include <stdio.h>
#include "focus_map.h"
#include "focus_dist.h"
#include "focus_pred.h"
int main(void) {
    for (unsigned v=0;v<65536;v++) {
        printf("%d %d %u %u %u %d %u\n",focus_em06_to_counts((uint16_t)v),
            focus_counts_for_code((uint16_t)v,500),focus_counts_to_em06((int32_t)v-1000),
            focus_distance_code((int32_t)v-1000,500),focus_distance_coarse((int32_t)v-1000,500),
            focus_log2_q6(v+1),focus_exp2_q6((int32_t)v));
    }
    for (int sign=-1;sign<=1;sign+=2) for(unsigned period=1;period<=100;period++) {
        struct focus_pred p;focus_pred_begin(&p,3000,3000+sign*2000,UINT32_MAX-50);
        for(unsigned t=0;t<200;t++) {
            int32_t pos=3000+sign*(int32_t)t*5;
            focus_pred_sample(&p,pos,UINT32_MAX-50+t);
            if(t==50)focus_pred_retarget(&p,3000+sign*1000);
            if(t==150)focus_pred_end(&p);
            printf("%d %d %u\n",focus_pred_ahead(&p,pos,(uint16_t)period),p.vel_q8,p.active);
        }
    }
    return 0;
}
