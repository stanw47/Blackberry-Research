================================================================================
SESSION 7Q - ext_csd REVEALS BOOT WP IS POWER-ON (TEMPORARY), NOT PERMANENT
================================================================================
2026-08-30, Classic (MSM8960). Follow-up to 7p (DCMD_MMCSD_WRITE_PROTECT EIO).

[1] WHAT WE DID
  - Computed DCMD_MMCSD_CARD_REGISTER = __DIOTF(_DCMD_CAM, _SIM_MMCSD+4,
    struct _mmcsd_card_register). struct = 24 bytes (action,type,address,length,
    rsvd[2]). => 0xC0181A14.
  - Issued READ ext_csd via ctypes (Disk_Drivers group -> berrycore python3.11).

[2] RESULT (KEY FINDING - major)
  ext_csd[170] BOOT_CONFIG_PROT = 0x00   (boot config NOT permanently protected)
  ext_csd[173] B_BOOT_WP       = 0x04   (bit2 = B_PWR_WP_EN only)
  ext_csd[162] B_BOOT_INFO     = 0x02
  raw[168:176] = 20 01 00 d0 00 04 0a 01
  => The boot-partition write-protect is POWER-ON PERIOD protection
     (B_PWR_WP_EN), i.e. TEMPORARY, re-applied each power-on. It is NOT
     permanent (BOOT_CONFIG_PROT=0, no B_PERM_WP_EN bit0).
  => Therefore boot0/boot1 ARE writable within a power-on session IF we can
     clear B_PWR_WP_EN (ext_csd[173] bit2) via CMD6 SWITCH (arg 0x03AD0000).

[3] CONFIRMED vs QNX-BBB REFERENCE DRIVER (markotikvic/QNX-BBB)
  mmcsd.c mmc_write_protect() (op=action, ptype, mode):
    - SET (op!=0): mmc_switch(EXT_CSD_BOOT_WP=173, mode)  [writes ext_csd[173]]
    - then mmc_sendcmd(SET_WRITE_PROT/CLR_WRITE_PROT) per wp_grp  [CMD28/29]
    - MMC_PTYPE_BOOT=0x01 ; EXT_CSD_BOOT_WP=173 ; EXT_CSD_USER_WP=171
  sim_mmc.c mmc_wp():
    - wp->mode &= MMCSD_WP_MODE_PWR_WP_EN (0x01)
    - EINVAL if slba>pend || (slba+nlba-1)>pend || nlba % wp_grp_size
    - else mmc_write_protect(); nonzero -> cam_devctl_status = EIO
  NOTE: wp_grp_size = HC_WP_GRP_SIZE * ERASE_GRP_SIZE * 512K. For this eMMC:
    raw[168]=0x20 (erase grp size=32), raw[171]=0xD0 (208) => wp grp huge
    (32*208*512K ~ 3.2 GB), so ANY nlba for boot0 (4MB) fails the
    nlba % wp_grp_size check -> EINVAL, NOT the SWITCH path.
  => That is why DCMD_MMCSD_WRITE_PROTECT SET mode=0 returned EIO: it never
     reached mmc_switch() because nlba=1 % wp_grp_size != 0. The driver
     WRITE_PROTECT path is effectively useless for boot partitions.

[4] LIVE TEST (confirmed) 
  BEFORE: ext_csd[170]=0x00 ext_csd[173]=0x04
  WRITE_PROTECT action=SET mode=0 nlba=1 -> ret=5 (EIO)
  AFTER:  ext_csd[170]=0x00 ext_csd[173]=0x04   (unchanged - as predicted)

[5] MMC DRIVER PROCESS (Classic, via pidin as root)
  Two instances of the driver, name = "sdmmc-rim-msmsdcc":
    pid 266271  (tid 1 = SIGWAITINFO, main)
    pid 1286155 (second instance - likely a second slot/card)
  Binary path not shown (name truncates). This is the process to patch with
  /proc/<pid>/as if we go the driver-memory-patch route.

[6] CONCLUSION / NEXT
  - Boot WP = B_PWR_WP_EN (temporary). Clearing it (CMD6 SWITCH ext_csd[173]=0)
    is the EXACT unlock. The driver's own WRITE_PROTECT devctl can't reach the
    SWITCH for boot partitions (wp_grp_size check).
  - The raw command path (DCMD_MMCSD_VUC_CMD=0xC0441A16) returned ENOTTY (7p) ->
    BlackBerry driver does NOT implement raw CMD6 passthrough. That is what
    sdmmc.zip adds ("MMC_IOC_CMD analogue").
  - Remaining free-software routes:
    (a) Patch sdmmc-rim-msmsdcc (pid 266271) memory via /proc/266271/as to add
        VUC_CMD / directly invoke mmc_sendcmd CMD6 SWITCH ext_csd[173]=0.
    (b) Find a setuid/setgid helper that already opens /dev/emmc and issues an
        arbitrary devctl (mmcsdpub only does devinfo).
  - If B_PWR_WP_EN is cleared, boot0 becomes writable -> write prototype
    bootloader (imggen) + set bbss.insecure (boot0@0x35a98=1) -> reboot.

ARTIFACTS:
  /tmp/pp/devctl_cardreg.py, devctl_wpclear.py  (ctypes probes)
  /tmp/pp/run_cardreg.py, run_wpclear.py       (paramiko runners)
  qnx-mmcsd-headers/dcmd_sim_mmcsd.h (struct + DCMD constants, lines 185-278)
================================================================================
