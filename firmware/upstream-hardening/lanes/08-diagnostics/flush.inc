void st_flush(int allowed, uint32_t ms, uint32_t rx_bytes,
              uint16_t errors, uint16_t status, uint8_t pins) {
    if (!allowed || failed || sealed || next_page>=ST_PAGE_COUNT) return;
    uint8_t p[ST_PAGE_BYTES];
    uint32_t key=st_lock();
    sealed=1;
    /* Summary goes first so a later torn event page cannot erase fault facts.
     * planned is a budget, not a claim that those writes subsequently succeed. */
    unsigned planned=4u*(ST_PAGE_COUNT-next_page-1u);
    if (planned>count) planned=count;
    unsigned omitted=(unsigned)dropped+count-planned;
    memset(p,0,sizeof(p));
    uint8_t *q=p+12;
    q[0]=stage; q[1]=connected; put16(q+2,fault); put32(q+4,ms);
    put16(q+8,rx_count); put16(q+10,tx_count); put32(q+12,rx_bytes);
    put16(q+16,errors); put16(q+18,status); put32(q+20,last_rx_ms);
    q[24]=first_rx; q[25]=last_rx; q[26]=first_tx; q[27]=last_tx;
    q[28]=capability; q[29]=pins;
    put16(q+30,(uint16_t)(omitted>65535u ? 65535u : omitted));
    q[32]=capability_seen;
    q[33]=1; q[34]=count; q[35]=(uint8_t)planned; q[36]=shutdown;
    if (!append(p,1,1)) { st_unlock(key); return; }
    while (flushed<planned) {
        memset(p,0,sizeof(p));
        uint8_t n=0;
        while (n<4 && flushed<planned) {
            unsigned i=flushed++;
            if (i>=24u) { i+=tail; if (i>=ST_EVENTS) i-=24u; }
            struct event *e=&events[i]; uint8_t *q=p+12+12*n++;
            put32(q,e->ms); q[4]=e->kind; q[5]=e->id; q[6]=e->cls; q[7]=e->seq;
            put16(q+8,e->length); put16(q+10,e->operand);
        }
        if (!append(p,2,n)) break;
    }
    st_unlock(key);
}
