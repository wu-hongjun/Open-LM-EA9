static uint8_t em_transmit(uint8_t *frame, uint16_t len)
{
	uint8_t snapshot[EM_OWNER_CAPACITY];
	uint16_t sum = 0;
	uint32_t key, generation;
	if (!frame || len < 9u || len > sizeof snapshot) return 0;

	/* Only foreground and the CS EIC callback edit templates. Foreground
	 * cannot overlap that callback: the CS counter changes before each ISR
	 * mutation. One generation-checked copy keeps SERCOM RX service live. */
	generation = em_cs_edges;
	__asm volatile ("" ::: "memory");
	memcpy(snapshot, frame, len);
	__asm volatile ("" ::: "memory");
	if (generation != em_cs_edges) return 0;
	snapshot[1] = (uint8_t)len;
	snapshot[2] = (uint8_t)(len >> 8);
	snapshot[len - 1] = EM_FRAME_END;
	for (uint16_t i = 1; i <= (uint16_t)(len - 4); i++) sum += snapshot[i];
	snapshot[len - 3] = (uint8_t)sum;
	snapshot[len - 2] = (uint8_t)(sum >> 8);

	/* The interrupt latch covers a complete pulse that has already returned
	 * low; the pin covers a rise before the filtered EIC latch has settled.
	 * Both are sampled inside the same short mask as asserting lens CS. */
	key = st_lock();
	if (generation != em_cs_edges || em_pin_level(EM_PIN_BODY_CS) || em_eic_receive_pending()
	    || (g_owner.phase && !em_owner_status_valid(&g_owner))
	    || (em_shutdown_requested() && !(g_shutdown.state == EM_SD_ACTIVE
	         && frame == g_shutdown.request))) {
		st_unlock(key);
		return 0;
	}
	PORT->Group[0].OUTSET.reg = (1u << EM_PIN_LENS_CS);
	st_unlock(key);
	if (!em_uart_send(snapshot, len)) {
		PORT->Group[0].OUTCLR.reg = (1u << EM_PIN_LENS_CS);
		return 0;
	}
	delay_us(EM_CS_HOLD_US);
	PORT->Group[0].OUTCLR.reg = (1u << EM_PIN_LENS_CS);
	em_frames_tx++;
	st_note(ST_TX,snapshot[5],snapshot[3],snapshot[4],len,0,millis());
	return 1;
}
