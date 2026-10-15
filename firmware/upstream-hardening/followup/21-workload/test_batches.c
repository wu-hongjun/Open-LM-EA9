/* All frames here are synthetic, including the header copied from the PUBLIC
 * A6000 state pattern. No captured private frames or factory bytes. */
#define main prior_flow_main
#include "flow_helpers.inc"
#undef main

static void batch(unsigned count, unsigned observed_header, unsigned *serial)
{
    uint8_t p[64]={0};
    const uint8_t state[13]={0,0,0x19,0x83,0,0,0x3b,0,0,0,1,0,0};
    unsigned room=EM_QUERY_Q-query_pending();
    p[3]=1;p[4]=0x72;p[5]=4;
    if(observed_header)memcpy(p+6,state,sizeof state);
    for(unsigned j=0;j<count;j++) {
        unsigned i=(*serial)++;
        uint8_t tag=(i&1)?EM_REC_Q_D2POS:EM_REC_Q_POS2D;
        uint16_t operand=(i&1)?(320+3*i):(4144+17*i);
        p[19+3*j]=tag;p[20+3*j]=operand;p[21+3*j]=operand>>8;
        if(j<room) {
            assert(want_n<32);want_tag[want_n]=tag;
            want_val[want_n++]=tag==EM_REC_Q_POS2D?focus_distance_code(focus_em06_to_counts(operand),EM_FOCAL_MM10):focus_counts_to_em06(focus_counts_for_code(operand,EM_FOCAL_MM10));
        }
    }
    seal(p,22+3*count);host_body_frame(p,22+3*count);
}
int main(int argc,char **argv)
{
    assert(argc==5);
    unsigned n=atoi(argv[1]),header=atoi(argv[2]),drive=atoi(argv[3]),cycles=atoi(argv[4]);
    unsigned serial=0,first=0,requested=n*cycles;
    assert(n<=5 && cycles<=8);
    em_init();frame(2,0x0a);em_poll();assert(em_handshake_done);sent_n=0;
    for(unsigned t=0;t<cycles;t++) {
        batch(n,header,&serial);
        if(drive)em_post_event(EM_REC_DRIVE,1);
        tick();collect();
        if(!t)first=got_n;
    }
    for(unsigned t=0;t<8;t++){tick();collect();}
    finish();
    assert(first==(n?(drive?1:(n<2?n:2)):0));
    if(cycles==1)assert(want_n==(n<4?n:4));
    if(cycles==8 && n==4 && !drive)assert(want_n==20 && got_n==20);
    if(cycles==8 && n==4 && drive)assert(want_n==14 && got_n==14);
    printf("SUMMARY requested=%u admitted=%u delivered=%u not_admitted=%u first_status_answers=%u\n",requested,want_n,got_n,requested-want_n,first);
}
