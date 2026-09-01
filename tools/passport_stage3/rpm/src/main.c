#include <stdint.h>
#include <string.h>

#define GCC_WDOG_DEBUG (*(volatile uint32_t*) 0xFC401780)
#define BOOT_PARTITION_SELECT (*(volatile uint32_t*) 0xFC4BE0F0)
#define RPM_APPS_STATUS_MAGIC (*(volatile uint32_t *) 0x100008)
#define RPM_IMAGE_DEST_PTR (*(volatile uint32_t *) 0x10000C)

#define apps_reset ((void (*)()) 0x2F8F5)

void stage2_main()
{
	uint32_t GCC_WDOG_DEBUG_original = GCC_WDOG_DEBUG;
	uint32_t BOOT_PARTITION_SELECT_original = BOOT_PARTITION_SELECT;
	
	// Enable debug mode
	GCC_WDOG_DEBUG = 0x20000;
	BOOT_PARTITION_SELECT = 0x5D1;

	apps_reset();
	
	// Wait for apps signaling it's ready
	while (RPM_APPS_STATUS_MAGIC != 0);
	RPM_IMAGE_DEST_PTR = 0;
	
	GCC_WDOG_DEBUG = GCC_WDOG_DEBUG_original;
	BOOT_PARTITION_SELECT = BOOT_PARTITION_SELECT_original;
}
