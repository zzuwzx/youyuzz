# ---- Youyuzz Switch Plugin Makefile ----
include $(DEVKITPRO)/libnx/switch_rules

TARGET      := youyuzz-switch
BUILD       := build
SOURCES     := src src/app src/gui src/net src/auth src/config src/notify src/utils
INCLUDES    := include src

ARCH := -march=armv8-a+crc+crypto -mtune=cortex-a57 -mtp=soft -fPIE

CFLAGS   := -g -Wall -O2 -ffunction-sections $(ARCH) $(DEFINES) $(INCLUDE) -D__SWITCH__ -I$(PORTLIBS)/include/SDL2
CXXFLAGS := $(CFLAGS) -fno-rtti -fno-exceptions -std=c++17
LDFLAGS  := -specs=$(DEVKITPRO)/libnx/switch.specs -g $(ARCH) -Wl,-Map,$(notdir $*.map)
LIBS     := -lSDL2 -lcurl -lmbedtls -lmbedx509 -lmbedcrypto -lnx
LIBDIRS  := $(PORTLIBS) $(LIBNX)

export OUTPUT := $(CURDIR)/$(TARGET)
export VPATH  := $(foreach dir,$(SOURCES),$(CURDIR)/$(dir))
export OFILES := $(addsuffix .o,$(notdir $(foreach dir,$(SOURCES),$(wildcard $(dir)/*.cpp) $(wildcard $(dir)/*.c))))
export INCLUDE := $(foreach dir,$(INCLUDES),-I$(CURDIR)/$(dir)) $(foreach dir,$(SOURCES),-I$(CURDIR)/$(dir))
export PATH := $(DEVKITPRO)/tools/bin:$(PATH)

.PHONY: $(BUILD) clean

$(BUILD):
	@[ -d $@ ] || mkdir -p $@
	@$(MAKE) --no-print-directory -C $@ -f $(CURDIR)/Makefile

clean:
	@echo clean ...
	@rm -fr $(BUILD) $(TARGET).nro $(TARGET).elf

$(OUTPUT).elf: $(OFILES)

$(OUTPUT).nro: $(OUTPUT).elf