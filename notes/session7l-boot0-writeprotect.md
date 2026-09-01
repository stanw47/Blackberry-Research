================================================================================
SESSION 7L - WRITE-ACCESS TEST RESULT: boot0 WRITE-PROTECTED (the wall) - 2026-08-30
================================================================================
Goal: determine if the Classic's eMMC boot partition is software-writable, to
decide if Balika can be replicated WITHOUT desolder.

[1] RESULT (definitive)
  - boot0 write: "dd: /dev/emmc/boot0: Read-only file system" (EROFS).
    The Disk_Drivers group HAS rw DAC, but the eMMC boot partition is
    write-protected at the hardware level.
  - User area is WRITABLE: uda0, os0, dmi0 all accepted writes (1+0 in/out).
  => The eMMC boot partitions (boot0/boot1) have BOOT_WP / BOOT_CONFIG_PROT
     set; the user area is normal R/W. This is EXACTLY the wall that Balika's
     desoldering was designed to bypass.

[2] WHAT THIS MEANS
  - Software write to boot0 (to set bbss_insecure + prototype bootloader) is
    BLOCKED from the running OS, even with the Disk_Drivers group.
  - Read access remains FULLY available (we already dumped everything).
  - The unlock therefore still requires a hardware path to write boot0:
    (a) ISP (test points, no desolder) - bypasses the OS/controller WP,
    (b) desolder + reader (Balika's original),
    (c) OR a way to toggle the eMMC boot-partition WP from software.

[3] REMAINING SOFTWARE ANGLES (not yet exhausted)
  1. BOOT_WP vs BOOT_CONFIG_PROT distinction:
     - BOOT_WP = power-on write protect (TEMPORARY; SBL1 sets it each boot).
       If only BOOT_WP is set, there may be a WINDOW early in boot (before
       SBL1 runs) where boot0 is writable. Hard to hit from the OS, but real.
     - BOOT_CONFIG_PROT = permanent (once set, cannot be cleared).
     - The SBL1 strings reference BOTH ("BOOT_WP", "BOOT_CONFIG_PROT").
  2. mmcsdpub (/base/bin/mmcsdpub, needs -f <rawdev>): likely reads CSD/
     ext_csd and may issue CMD6 SET_BOOT_CONFIG (toggle WP). It FAILS as nto:
       "Failed to create /fs/pps/qnx/device" (needs PPS permission). Could try
       via a higher group (g_<pps group>) - next step.
  3. mod_nvram (getroot) already ran; nvram0 build-info shows INsecure (field8=1)
     while boot0 shows SECURE - confirms the rootkit touched nvram, not boot0.

[4] WHAT WE DID ACHIEVE (regardless of the WP wall)
  - Full raw eMMC READ access via g_Disk_Drivers (software, no hardware).
  - Full dumps: boot0/boot1/nvram0/dmi0 -> /home/stanw47/priv-research/classic-emmc/.
  - Pinned "bbss.insecure" = build-info field8 (u32) @ boot0 offset 0x35a98
    (currently 0 = SECURE; nvram0 copy = 1 = INsecure).
  - Decoded the full imggen unlock toolchain (prototype bootloader + HWI + GPT).
  - Mapped the write-protect scope precisely (boot0 RO, user area RW).

[5] NEXT STEPS (ranked)
  1. Try mmcsdpub via a group that can create /fs/pps/qnx/device (find the PPS
     group; e.g. g_nto failed, try a broader group or the __android_* tools).
     Goal: read ext_csd -> determine BOOT_WP vs BOOT_CONFIG_PROT.
  2. If BOOT_WP is temporary: attempt a write in the post-reboot window (risky,
     needs timing). If permanent: software is dead, hardware (ISP) is required.
  3. Hardware fallback (unchanged): ISP test points (no desolder) is the
     definitive non-destructive write path for boot0.

ARTIFACTS: session7j/7k/7l notes; dumps in priv-research/classic-emmc/; imggen
  in /tmp/opencode/imggen/ (should be moved to durable storage).
================================================================================
