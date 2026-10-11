# Application-only release. No diagnostic flash writers are compiled.
DEPS ?= ../../tools/firmware-deps
ARM := $(DEPS)/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-
CC := $(ARM)gcc
FLAGS := -mthumb -mcpu=cortex-m0plus -O2 -DNDEBUG -DEA9_NO_LOG -D__SAMD21E17A__ -ffunction-sections -fdata-sections -fno-common -Wall -Wextra -std=gnu99 -g -MMD -MP
INC := -Isrc -I$(DEPS)/samd21-dfp-2/samd21a/include -I$(DEPS)/CMSIS_5-5.9.0/CMSIS/Core/Include
SOURCES := startup_samd21 system_samd21 board clock delay emount emount_packets em_uart em_eic motor metadata_main lens_profile
OBJS := $(addprefix build/,$(addsuffix .o,$(SOURCES)))
AF_SOURCES := startup_samd21 system_samd21 board clock delay emount emount_packets em_uart em_eic motor main lens_profile abs_encoder servo focus_map focus_dist focus_pred vdd af_control io_guard af_reference af_completion
AF_OBJS := $(addprefix build/reconciled/,$(addsuffix .o,$(AF_SOURCES)))
all: build/ea9-profile-template.bin
upstream-af: build/af/ea9-af-template.bin
reconciled-af: build/reconciled/ea9-af-reconciled-template.bin
build/%.o: src/%.c Makefile
	@mkdir -p build
	$(CC) $(FLAGS) $(INC) -c $< -o $@
build/ea9-profile-template.elf: $(OBJS) src/ea9.ld
	$(CC) $(OBJS) -mthumb -mcpu=cortex-m0plus -Tsrc/ea9.ld -Wl,--gc-sections,-Map=build/ea9-profile-template.map --specs=nano.specs --specs=nosys.specs -o $@
	$(ARM)size $@
	@if $(ARM)nm $@ | grep -qE ' (diag_|trail_)'; then echo 'Flash logging survived'; exit 1; fi
	@if $(ARM)nm $@ | grep -qE ' (motor_drive|motor_brake|motor_home|servo_)'; then echo 'Motion survived the metadata-only build'; exit 1; fi
build/ea9-profile-template.bin: build/ea9-profile-template.elf
	$(ARM)objcopy -O binary --gap-fill=0xff $< $@
build/reconciled/%.o: src/%.c Makefile
	@mkdir -p build/reconciled
	$(CC) $(FLAGS) -DEA9_AF_BUILD -DEM_FW_VERSION_BCD=0x22u -DEA9_PROFILE_ADDRESS=0x9f00u $(INC) -c $< -o $@
build/reconciled/ea9-af-reconciled-template.elf: $(AF_OBJS) src/ea9.ld
	$(CC) $(AF_OBJS) -mthumb -mcpu=cortex-m0plus -Wl,--defsym=EA9_PROFILE_AT=0x9f00 -Tsrc/ea9.ld -Wl,--gc-sections,-Map=build/reconciled/ea9-af-reconciled-template.map --specs=nano.specs --specs=nosys.specs -o $@
	$(ARM)size $@
	@if $(ARM)nm $@ | grep -qE ' (diag_|trail_)'; then echo 'Flash logging survived'; exit 1; fi
	@$(ARM)nm $@ | grep -q ' T servo_move_rel' || { echo 'AF servo missing'; exit 1; }
	@$(ARM)nm $@ | grep -q ' T motor_drive' || { echo 'AF motor driver missing'; exit 1; }
build/reconciled/ea9-af-reconciled-template.bin: build/reconciled/ea9-af-reconciled-template.elf
	$(ARM)objcopy -O binary --gap-fill=0xff $< $@
build/af/ea9-af-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-template.bin
	@mkdir -p build/af
	cp $< $@
-include $(OBJS:.o=.d) $(AF_OBJS:.o=.d)
.PHONY: all upstream-af reconciled-af
