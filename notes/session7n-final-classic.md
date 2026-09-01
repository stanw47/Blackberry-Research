================================================================================
SESSION 7N - FINAL: Classic unlock fully mapped; software path exhausted - 2026-08-30
================================================================================

[1] passport_stage3 DECODED (the SOFTWARE unlock path - and why it's gated)
  - rpm/src/main.c: runs ON the RPM co-processor. Sets two magic registers:
      GCC_WDOG_DEBUG      (0xFC401780) = 0x20000   (disable watchdog reset)
      BOOT_PARTITION_SELECT(0xFC4BE0F0) = 0x5D1     (PBL debug-mode selector)
    then apps_reset() (0x2F8F5). The AP's PBL then sees BOOT_PARTITION_SELECT
    =0x5D1 -> enters DEBUG mode -> skips signature verification -> jumps to a
    trampoline (0xFE800000 -> 0xFE820000) that uses PBL SDCC/GPT to load ANY
    SBL1 from eMMC.
  - make_stage3.cpp: stage3.mbn is an ELF (entry 0xFE800000) that writes RPM
    code to 0xFC100080, starts RPM (0xFC100008=0xA4CD7EA2), and embeds the apps
    payload at 0xFE820000.
  - The magic registers live in the 0xFC4xxxxx boot-config/fuse region - NOT
    reachable from the OS. Loading stage3.mbn requires the PBL to already be in
    download/debug mode (Sahara/EDL-style), which is hardware/key-gated.
  => stage3 is NOT a software path from the running OS. Same gate as EDL.

[2] BOOT MODES (from boot0/SBL1 strings)
  - No fastboot/recovery/download/EDL/Sahara/9008 strings in SBL1.
  - Only "factory boot mode" vs "product boot mode" (both OS-type gated).
  - "boot partition detection failure; default BOOT0", "Backup boot key combo
    active", "Debug board switch forcing backup boot chain" = boot-chain
    fallback only, not an unlock.

[3] WRITE-PROTECT STATUS (final, definitive)
  - boot0: "Read-only file system" (EROFS) -> write-protected.
  - boot1: "Read-only file system" (EROFS) -> write-protected.
  - rpmb0: "Inappropriate I/O control operation" (RPMB needs authenticated write).
  - uda0/os0/dmi0: WRITABLE (user area).
  => Both eMMC boot partitions are hardware write-protected. Software cannot
     write the prototype bootloader. This is EXACTLY why Balika desoldered.

[4] THE COMPLETE CLASSIC UNLOCK PICTURE (final)
  REQUIREMENTS to run LineageOS on Classic/Passport:
    a) Write prototype bootloader (stage1/2/3+bbss+sbl1+aboot) to boot0/boot1
       -> BLOCKED (boot partition WP).
    b) OR trigger PBL debug mode (stage3) -> BLOCKED (needs PBL download mode).
  BOTH require HARDWARE: ISP test points (no desolder) or desolder.
  The SOFTWARE path is fully exhausted. The getroot userland root + BerryCore
  is the software ceiling for these devices.

[5] ACHIEVEMENTS THIS ARC (7J-7N) - durable value
  1. Raw eMMC READ via g_Disk_Drivers setgid wrapper (software, no hardware).
  2. Full dumps: boot0/boot1/nvram0/dmi0 -> priv-research/classic-emmc/.
  3. Pinned "bbss.insecure" = build-info field8 (u32) @ boot0 0x35a98 (=0 SECURE;
     nvram0 copy =1 INsecure, a getroot mod_nvram artifact).
  4. Decoded imggen (prototype bootloader + HWI text + GPT) -> priv-research/imggen/.
  5. Decoded passport_stage3 (PBL debug mode) -> priv-research/passport_stage3/.
  6. Mapped the ~400 g_<group> setgid wrappers (getroot's group-escalation model).
  7. Confirmed: user area writable, boot partitions RO, RPMB authenticated-only.

[6] STRATEGIC CONCLUSION (all 3 devices)
  - Classic/Passport: ROOTED (getroot). Unlock = HARDWARE (ISP/desolder). The
    exact byte to flip (boot0@0x35a98) is now known for when hardware is used.
  - Priv: unchanged - root requires a kernel 0-day (no public one) or ISP to
    write hlos_unsigned.tkn to nvuser (which is NOT HW-WP'd, unlike boot0). The
    Priv's block devices are SELinux-gated (no g_Disk_Drivers equivalent).
  - The "checks everywhere" hypothesis is fully confirmed; BIDE/Pathtrust are
    defensively written; the unlock is gated at the HARDWARE boot-partition
    write-protect, which is the layer Balika's desoldering was built to cross.

ARTIFACTS: session7j-7n notes; classic-emmc/*.img; imggen/; passport_stage3/.
================================================================================
