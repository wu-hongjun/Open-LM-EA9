/* C test mains bypass Reset_Handler. Reproduce only its production packet
 * initialization call; compiled reset/IRQ order is checked separately. */
extern void ea9_packets_init(void);
__attribute__((constructor)) static void initialize_test_packets(void)
{ ea9_packets_init(); }
