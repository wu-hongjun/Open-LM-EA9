include release.mk
$(OBJDIR)/em_uart.o $(OBJDIR)/em_eic.o $(OBJDIR)/abs_encoder.o $(OBJDIR)/motor.o $(OBJDIR)/servo.o: CFLAGS += -O2

OBJS += $(OBJDIR)/reported_aperture.o
build/ea9-rebuild-release.elf: $(OBJDIR)/reported_aperture.o
