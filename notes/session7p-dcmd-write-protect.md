================================================================================
SESSION 7P - FREE ALTERNATIVE TO sdmmc.zip: QNX DCMD_MMCSD_WRITE_PROTECT - 2026-08-30
================================================================================
Goal: find a way to toggle the boot0/boot1 write-protect WITHOUT the Patreon-only
sdmmc.zip patch, now that we have root on Classic + Passport.

[1] THE FINDING (major)
  The QNX mmc driver (devb-sdmmc / devb-mmcsd) exposes STANDARD devctl commands
  that do exactly what sdmmc.zip's "MMC_IOC_CMD analogue" adds:
    - DCMD_MMCSD_WRITE_PROTECT = __DIOTF(_DCMD_CAM, _SIM_MMCSD + 1, struct _mmcsd_write_protect)
        "Clear or set write protection"
    - DCMD_MMCSD_VUC_CMD       = __DIOTF(_DCMD_CAM, _SIM_MMCSD + 6, struct _mmcsd_vuc_cmd)
        "Execute a vendor-unique command" (raw MMC CMD passthrough)
    - DCMD_MMCSD_RPMB_RW_FRAME / DCMD_MMCSD_CARD_REGISTER (read ext_csd, etc.)
  Source: QNX docs + qnx/bsp + markotikvic/QNX-BBB (open-source mmcsd driver).
  Header saved: priv-research/qnx-mmcsd-headers/dcmd_sim_mmcsd.h (+ sim_mmc.h).

[2] THE EXACT STRUCT + CONSTANTS (from dcmd_sim_mmcsd.h)
  MMCSD_WRITE_PROTECT (32 bytes):
    +0x00 uint32 action    MMCSD_WP_ACTION_CLR=0x00  / MMCSD_WP_ACTION_SET=0x01
    +0x04 uint32 mode      MMCSD_WP_MODE_PWR_WP_EN=0x01  (power-on period = BOOT_WP)
    +0x08 uint64 lba
    +0x10 uint64 nlba
    +0x18 uint64 rsvd2
  MMCSD_VUC_CMD (raw command): has opcode, flags (DATA/RESP types), arg, resp[4],
    blk_sz, data_ptr, data_len, timeout - i.e. a full MMC CMD passthrough.

[3] CONFIRMED CONSTANTS (decoded from QNX headers, 2026-08-30)
  devctl encoding (devctl.h):
    __DIOTF(class,cmd,data) = (sizeof(data)<<16) + (class<<8) + cmd + 0xC0000000
    _DCMD_CAM = 0x0C ; _CAM_SIM = 2000 ; _SIM_MMCSD = 2000 + 16*100 = 3600
  => DCMD_MMCSD_WRITE_PROTECT = 0xC0201A11   (struct 32 bytes)
     DCMD_MMCSD_VUC_CMD       = 0xC0441A16   (struct 68 bytes)
     DCMD_MMCSD_GET_CSD       = __DIOTF(0x0C, 3602, MMCSD_CSD)
  Headers saved: priv-research/qnx-mmcsd-headers/{dcmd_sim_mmcsd.h, sim_mmc.h,
  dcmd_cam.h}. Full BB10 SDK header dump: github.com/djbclark/bb10qnx.

[3b] LIVE TEST RESULT (2026-08-30, Classic, via ctypes + devctl)
  - python3.2 (/usr/bin) = stub linking libpython3.2m.so.1.0, stdlib missing
    (PYTHONHOME issue). BerryCore python3.11 = full but pathtrust-blocked AS ROOT
    (untrusted /accounts path). WORKING route: g_Disk_Drivers -> ksh (Disk_Drivers
    group) -> berrycore python3.11 -> devctl (Disk_Drivers group suffices to open
    boot0 O_RDWR + issue the devctl).
  - DCMD_MMCSD_WRITE_PROTECT is IMPLEMENTED (driver validates: nlba=0xFFFF... ->
    ret=22 EINVAL). But:
        boot0 CLR (nlba=1, 8192) -> ret=5 EIO
        boot1 CLR               -> ret=5 EIO
  - QNX devctl returns POSITIVE errno (not -1). ret=5 = EIO.
  => The boot-partition write-protect is NOT clearable via DCMD_MMCSD_WRITE_PROTECT
     on this device (permanent BOOT_CONFIG_PROT, or the driver's boot-WP path
     fails). This is consistent with boot0/boot1 dd = EROFS even as root.

[3c] REMAINING SOFTWARE PATH
  - DCMD_MMCSD_VUC_CMD (0xC0441A16) = raw MMC command passthrough. Could send
    CMD6 SWITCH arg=0x03AD0000 (write ext_csd[173] BOOT_WP = 0) to try clearing
    the boot WP directly, bypassing mmc_write_protect(). Untested. Needs the
    MMCSD_VUC_CMD struct filled (opcode, flags, arg, resp[4], data_ptr phys, etc.)
    - this is the last free-software shot before Patreon sdmmc.zip / ISP.

[4] OPEN QUESTIONS / CAVEATS
  - BlackBerry may use the NEWER DCMD_SDMMC_* framework (mmcsdpub uses
    DCMD_MMCSD_DEVINFO which is NOT in dcmd_sim_mmcsd.h). Must verify the device
    driver actually handles DCMD_MMCSD_WRITE_PROTECT (test with a GET first, or
    just issue CLR and re-test boot0 write).
  - _DCMD_CAM + _SIM_MMCSD values still needed (fetch QNX SDK sys/dcmd_cam.h /
    hw/sim_mmcsd.h, or reverse from the mmcsd driver binary on device).
  - Even if WRITE_PROTECT works, the eMMC may have BOOT_CONFIG_PROT (permanent)
    set, in which case only the user-area WP is toggleable (not boot partitions).

ARTIFACTS: priv-research/qnx-mmcsd-headers/{dcmd_sim_mmcsd.h,sim_mmc.h};
  QNX-BBB driver clone at /tmp/qnx-bbb (volatile).
================================================================================
