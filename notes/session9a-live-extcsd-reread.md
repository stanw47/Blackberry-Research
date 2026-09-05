===============================================================================
SESSION 9A - LIVE EXT_CSD RE-READ (Windows SSH + Disk_Drivers wrapper) 2026-09-04
===============================================================================
Context: Re-check current boot-partition WP state on the Classic (device booted
many times since 7q). Goal: confirm whether the WP is still TEMPORARY
(B_PWR_WP_EN, clearable in-session) vs PERMANENT (fused) -- decides software
(Option B / C) vs hardware (desolder) path for the LineageOS endgame.

[1] CHANNEL (established this session)
  - SSH as devuser (paramiko 3.5.1, auth_timeout=120) to 169.254.0.1:22 through
    the still-running blackberry-connect tunnel (java pid 41148).
  - Push script via sftp to /accounts/1000/shared/misc/extcsd_read.py.
  - Run: echo "exec /accounts/1000/shared/misc/berrycore/bin/python3.11 <py>" \
         | /base/bin/g_Disk_Drivers
  - ctypes devctl DCMD_MMCSD_CARD_REGISTER 0xC0181A14, struct
    MMCSD_CARD_REGISTER (24B: action,type,address,length,rsvd[2] + 512B data)
    ACTION_READ(0) / REG_TYPE_EXT_CSD(2) / address=0 / length=512.
  - devctl ret 0 for boot1 and uda0.

[2] RESULTS (LIVE CHIP, all boot-relevant registers)
  raw[160:192] = 03 00 02 00 00 00 05 1f 04 01 00 d0 00 04 0a 01 00 04 10 08 ...
  ext_csd[162] B_BOOT_INFO        = 0x02
  ext_csd[168] ERASE_GRP_SIZE     = 0x04
  ext_csd[170] BOOT_CONFIG_PROT   = 0x00   (boot config NOT permanently protected)
  ext_csd[173] BOOT_WP            = 0x04   (bit2 B_PWR_WP_EN = POWER-ON WP only)
  ext_csd[174] BOOT_WP_STATUS     = 0x0a   (0x08 | 0x02: per-WP-state bits)
  ext_csd[177] BOOT_BUS_WIDTH     = 0x04
  ext_csd[179] PARTITION_CONFIG   = 0x08   (boot source = boot0, matches Balika's
                                  "mmc bootpart enable 1 0" target value)
  NOTE: boot0 O_RDWR open returns EROFS (30) -- the MMC driver itself refuses
  R/W open of the write-protected boot0 partition; boot1 opens O_RDWR (the
  B_SEL_WP bit selects boot0 as the write-protect target).

[3] INTERPRETATION (matches 7q/8c conclusions, now fresh)
  - WP is TEMPORARY (power-on period), NOT fused: BOOT_CONFIG_PROT=0 means
    ext_csd[173..179] are NOT permanent-protected -> a CMD6 SWITCH writing
    ext_csd[173]=0 WOULD clear boot0 boot-partition write-protect.
  - The ONLY reason it hasn't worked: the BB driver's stock WRITE_PROTECT
    devctl path is gated by the wp_grp_size check (EIO, 7q[3]) and VUC_CMD
    (raw CMD6 passthrough) returns ENOTTY (7p[3c]).
  - => Hardware is PERFECTLY clearable. Software just needs a way to reach a
     CMD6 SWITCH (0x03AD0000 -> ext_csd[173]=0) or any other way to clear
     B_PWR_WP_EN for the current session; then boot0 becomes R/W and the 7q
     plan (write imggen prototype bootloader + bbss.insecure flag) is live.

[4] RANKED PATHS TO SEND THE CMD6 (current)
  a) Driver .data/.got hook: rewrite a function pointer on the devctl path to
     redirect into existing mmc_switch (0x76c0 -> 0x8240 CMD6). Needs
     /proc/<pid>/as R/W. NOTE: as devuser /proc/.../as is EPERM (pidin spam
     observed). Root was previously obtained via pathtrust __root trick
     (README point 1) -- rerun that to get real uid-0 back.
  b) Driver thread hijack via /proc/<pid>/ctl + DCMD_PROC_STOP/SETGREG to call
     mmc_switch directly. Also needs root-ish /proc ctl access.
  c) CMD6 from an unprivileged group wrapper that ALSO has open-on /dev/emmc:
     none of the ~200 g_* wrappers open /dev/emmc and issue arbitrary devctls
     (only mmcsdpub devinfo). Dead for now.
  d) Desolder / ISP buffer (Option A) or RAMLoader signature exploit (Option C)
     remain the off-device fallbacks.

[5] CONFIDENT WHICH-CLASSIC-GOES-LAST
  - Classic = perfect TEST-MULE for the boot0-unlock + bootloader-replace
    technique (identical MSM8960 + eMMC boot flow per bb-usbdl; same ext_csd
    layout). If the unlock succeeds here, the same in-session CMD6 approach
    transfers to the Passport.
  - Passport then gets the real prize: boot via LineageOS (imggen'd boot0 +
    fastboot + lineage-18.1). Classic has NO Android port even if unlocked --
    its reward is proving the technique + a re-flashable BB10.

ARTIFACTS: local wins push_run.py / extcsd_read.py (Temp\opencode); device:
  /accounts/1000/shared/misc/extcsd_read.py
===============================================================================