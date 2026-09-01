/* key constants extracted from QNX SDK (full header: github djbclark/bb10qnx) */
#define _DCMD_CAM 0x0C
#define _CAM_SIM 2000
#define _SIM_MMCSD (_CAM_SIM + (16*100))  /* 3600 */
#define _SIM_SDMMC (_CAM_SIM + (17*100))  /* 3700 */
/* devctl encoding (devctl.h):
   __DIOTF(class,cmd,data) = (sizeof(data)<<16) + (class<<8) + cmd + 0xC0000000
   _POSIX_DEVDIR_TOFROM = 0xC0000000 */
