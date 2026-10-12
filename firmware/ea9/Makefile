# Application-only release. No diagnostic flash writers are compiled.
DEPS ?= ../../tools/firmware-deps
ARM := $(DEPS)/arm-gnu-toolchain-14.2.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-
CC := $(ARM)gcc
FLAGS := -mthumb -mcpu=cortex-m0plus -O2 -DNDEBUG -DEA9_NO_LOG -D__SAMD21E17A__ -ffunction-sections -fdata-sections -fno-common -Wall -Wextra -std=gnu99 -g -MMD -MP
INC := -Isrc -I$(DEPS)/samd21-dfp-2/samd21a/include -I$(DEPS)/CMSIS_5-5.9.0/CMSIS/Core/Include
AF_SOURCES := startup_samd21 system_samd21 board clock delay emount emount_packets em_uart em_eic motor main lens_profile lens_aperture abs_encoder factory_af factory_servo focus_map focus_dist focus_pred focus_motion vdd af_control io_guard af_reference af_completion
AF_OBJS := $(addprefix build/serviced/,$(addsuffix .o,$(AF_SOURCES)))
# Released 2.0–2.8 artifacts remain frozen. Current source builds AF 2.9.
all: build/ea9-profile-template.bin
upstream-af: build/af/ea9-af-template.bin
reconciled-af: build/reconciled/ea9-af-reconciled-template.bin
hardened-af: build/hardened/ea9-af-hardened-template.bin
factory-af: build/factory/ea9-af-factory-template.bin
refined-af: build/refined/ea9-af-refined-template.bin
audited-af: build/audited/ea9-af-audited-template.bin
polished-af: build/polished/ea9-af-polished-template.bin
observed-af: build/observed/ea9-af-observed-template.bin
serviced-af: build/serviced/ea9-af-serviced-template.bin
build/observed/ea9-af-observed-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-observed-template.bin
	@mkdir -p build/observed
	cp $< $@
build/polished/ea9-af-polished-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-polished-template.bin
	@mkdir -p build/polished
	cp $< $@
build/audited/ea9-af-audited-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-audited-template.bin
	@mkdir -p build/audited
	cp $< $@
build/refined/ea9-af-refined-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-refined-template.bin
	@mkdir -p build/refined
	cp $< $@
build/factory/ea9-af-factory-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-factory-template.bin
	@mkdir -p build/factory
	cp $< $@
build/hardened/ea9-af-hardened-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-hardened-template.bin
	@mkdir -p build/hardened
	cp $< $@
build/ea9-profile-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-profile-template.bin
	@mkdir -p build
	cp $< $@
build/reconciled/ea9-af-reconciled-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-reconciled-template.bin
	@mkdir -p build/reconciled
	cp $< $@
build/serviced/%.o: src/%.c Makefile
	@mkdir -p build/serviced
	$(CC) $(FLAGS) -DEA9_AF_BUILD -DEA9_FACTORY_AF -DEM_FW_VERSION_BCD=0x29u -DEA9_PROFILE_ADDRESS=0x9f00u $(INC) -c $< -o $@
build/serviced/ea9-af-serviced-template.elf: $(AF_OBJS) src/ea9.ld
	$(CC) $(AF_OBJS) -mthumb -mcpu=cortex-m0plus -Wl,--defsym=EA9_PROFILE_AT=0x9f00 -Tsrc/ea9.ld -Wl,--gc-sections,-Map=build/serviced/ea9-af-serviced-template.map --specs=nano.specs --specs=nosys.specs -o $@
	$(ARM)size $@
	@if $(ARM)nm $@ | grep -qE ' (diag_|trail_)'; then echo 'Flash logging survived'; exit 1; fi
	@$(ARM)nm $@ | grep -q ' T factory_servo_move_to' || { echo 'AF servo missing'; exit 1; }
	@$(ARM)nm $@ | grep -q ' T motor_drive' || { echo 'AF motor driver missing'; exit 1; }
build/serviced/ea9-af-serviced-template.bin: build/serviced/ea9-af-serviced-template.elf
	$(ARM)objcopy -O binary --gap-fill=0xff $< $@
build/af/ea9-af-template.bin: ../../apps/macos/Sources/DeviceKit/Resources/ea9-af-template.bin
	@mkdir -p build/af
	cp $< $@
-include $(AF_OBJS:.o=.d)
.PHONY: all upstream-af reconciled-af hardened-af factory-af refined-af audited-af polished-af observed-af serviced-af
