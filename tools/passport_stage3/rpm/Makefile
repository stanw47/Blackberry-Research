rwildcard = $(foreach d, $(wildcard $1*), $(filter $(subst *, %, $2), $d) $(call rwildcard, $d/, $2))

CROSS_COMPILE = arm-none-eabi-

# Use our cross-compile prefix to set up our basic cross compile environment.
CC      = $(CROSS_COMPILE)gcc
LD      = $(CROSS_COMPILE)ld
OBJCOPY = $(CROSS_COMPILE)objcopy

name := stage3

dir_source := src
dir_build := build
dir_out := out

ARCH := -mthumb -mfloat-abi=softfp -Wa,-mimplicit-it=thumb

ASFLAGS := $(ARCH) -nostdlib -static -fvisibility=hidden

# For debug builds, replace -O2 by -Og and comment -fomit-frame-pointer out
CFLAGS = \
	$(ARCH) \
	-g \
	-fomit-frame-pointer \
	-ffunction-sections \
	-fdata-sections \
	-std=gnu11 \
	-Werror \
	-Wall \
	-nostdlib \
	-Wno-multichar \
	-static -fvisibility=hidden

LDFLAGS = -specs=linker.specs -g $(ARCH) -nostdlib -static -fvisibility=hidden -Wl,--version-script=linker.version -Wl,--build-id=none

objects =	$(patsubst $(dir_source)/%.s, $(dir_build)/%.o, \
			$(patsubst $(dir_source)/%.c, $(dir_build)/%.o, \
			$(call rwildcard, $(dir_source), *.s *.c)))

define bin2o
	bin2s $< | $(AS) -o $(@)
endef

.PHONY: all
all: $(dir_out)/$(name).bin

.PHONY: clean
clean:
	@rm -rf $(dir_build)
	@rm -rf $(dir_out)

$(dir_out)/$(name).bin: $(dir_build)/$(name).elf
	@mkdir -p "$(@D)"
	@$(OBJCOPY) -S -O binary $< $@

$(dir_build)/$(name).elf: $(objects)
	@mkdir -p "$(@D)"
	@$(LINK.o) $(OUTPUT_OPTION) $^

$(dir_build)/%.bin.o: $(dir_build)/%.bin
	@mkdir -p "$(@D)"
	@$(bin2o)

$(dir_build)/%.o: $(dir_source)/%.c
	@mkdir -p "$(@D)"
	@$(COMPILE.c) $(OUTPUT_OPTION) $<

$(dir_build)/%.o: $(dir_source)/%.s
	@mkdir -p "$(@D)"
	@$(COMPILE.c) -march=armv8-a -x assembler-with-cpp $(OUTPUT_OPTION) $<

	
