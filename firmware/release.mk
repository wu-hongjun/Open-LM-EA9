# Release-only rules. Source/ordering/flags reproduce the working 4.5 image.
TOOLCHAIN ?= arm-none-eabi-
CC := $(TOOLCHAIN)gcc
SIZE := $(TOOLCHAIN)size
OBJDIR := build/obj-release
TARGET := build/ea9-rebuild-release
OPT ?= -Os
CFLAGS := -mthumb -mcpu=cortex-m0plus $(OPT) -DNDEBUG -DEA9_NO_LOG -D__SAMD21E17A__ \
          -ffunction-sections -fdata-sections -fno-common -Wall -Wextra -std=gnu99 -g -MMD -MP
LDFLAGS := -mthumb -mcpu=cortex-m0plus -Tsrc/ea9.ld -Wl,--gc-sections \
           -Wl,-Map=$(TARGET).map --specs=nano.specs --specs=nosys.specs
SRCS := src/startup_samd21.c src/system_samd21.c src/board.c src/clock.c src/delay.c \
        src/emount.c src/emount_packets.c src/optical_file.c src/em_uart.c src/em_eic.c \
        src/motor.c src/abs_encoder.c src/servo.c src/focus_map.c src/focus_dist.c src/vdd.c src/main.c
OBJS := $(patsubst src/%.c,$(OBJDIR)/%.o,$(SRCS))
-include $(OBJS:.o=.d)
$(OBJDIR):
	mkdir -p $@
$(OBJDIR)/%.o: src/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@
$(TARGET).elf: $(OBJS)
	$(CC) $(OBJS) $(LDFLAGS) -o $@
	$(SIZE) $@
