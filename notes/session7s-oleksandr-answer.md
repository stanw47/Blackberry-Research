================================================================================
SESSION 7S - OLEKSANDR'S ANSWER + MOUNT-STATE ANALYSIS - 2026-08-30
================================================================================

[1] OLEKSANDR'S ANSWER (verbatim intent)
  "a good mood and plenty of time are certainly nice, but modifying the emmc
   firmware without the proper knowledge will destroy the device. Reading the
   eMMC firmware works fine on the Z30, but on the passport, only the same
   block is read over and over again. Most likely, this requires unmounting
   the eMMC file systems and trying to read them with exclusive access. The
   driver patch simply implements the execution of any emmc command."

  KEY TAKEAWAYS:
  - CONFIRMS: sdmmc.zip driver patch = "execute any emmc command" = raw MMC
    command passthrough (the DCMD_MMCSD_VUC_CMD / MMC_IOC_CMD analogue I found
    is MISSING in the stock driver -> ENOTTY). My RE conclusion is correct.
  - The "same block read repeatedly" on Passport = eMMC partition caching
    artefact; fix = UNMOUNT filesystems + exclusive access before raw read.
  - Strong brick warning: don't modify firmware without knowing the format.
  - Z30 = MSM8960 (SAME SoC as Classic). "Reading works fine on Z30" => my
    Classic raw-read path should work. Passport = MSM8974AA (the repeated-block
    device).

[2] CLASSIC MOUNT STATE (as root, 2026-08-30)
  /dev/emmc/user0      -> /        (qnx6)
  /dev/emmc/user0      -> /sdcard  (qnx6)
  /dev/emmc/user0      -> /data    (qnx6)
  /dev/emmc/cal_work0  -> /efs     (qnx6)
  /dev/emmc/radio0t179 -> /radio   (rcfs)
  /dev/emmc/os0t179    -> /base    (rcfs)
  /dev/emmc/sd0        -> /accounts/1000/removable/sdcard (dos/fat32)
  boot0 / boot1 are NOT mounted (raw boot partitions).
  => The EIO on WRITE_PROTECT devctl is NOT from a mounted boot0 (it's not
     mounted). It comes from the driver's own 0xe53a availability check
     (returns !=1 for boot0 despite CARD_REGISTER succeeding -> likely a
     per-partition "attached/active" flag at [ext + target*0x2c8 + lun*0x58
     + 0x1f8] being 0 for boot partitions until some activation sequence).

[3] IMPLICATIONS / NEXT
  - Free path to boot0 write is confirmed technically possible (B_PWR_WP_EN is
    temporary; driver HAS the CMD6 SWITCH to ext_csd[173]).
  - The gate is the driver's partition-availability flag + the missing VUC_CMD.
  - Two concrete options:
    (a) Patch sdmmc-rim-msmsdcc memory via /proc/<pid>/as to add VUC_CMD
        (route 0xC0441A16 -> mmc_switch/hba raw CMD6), OR to set the partition
        "attached" flag so WRITE_PROTECT reaches the 0xad switch.
    (b) Use the WRITE_PROTECT devctl correctly if we can figure the activation
        sequence that sets [part+0x1f8] (maybe open O_EXCL, or issue a
        DCMD_MMCSD_GET_CID first to "attach").
  - MUST unmount / (user0), /base (os0t179), /radio (radio0t179), /efs before
    raw/exclusive access, per Oleksandr, to avoid the repeated-block artefact
    and to avoid corrupting mounted fs.
  - WARNING: firmware writes can brick. Only write boot0@0x35a98 (bbss.insecure)
    + prototype bootloader AFTER backing up boot0 (already dumped to
    classic-emmc/boot0.img).

ARTIFACTS:
  /home/stanw47/priv-research/work/session7r-sdmmc-driver-re.md (driver RE)
  /home/stanw47/priv-research/sdmmc-driver/devb-sdmmc-rim-msmsdcc (binary)
================================================================================
