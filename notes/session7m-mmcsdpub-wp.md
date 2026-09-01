================================================================================
SESSION 7M - mmcsdpub + WP determination attempt (blocked) - 2026-08-30
================================================================================
Goal: read ext_csd / determine BOOT_WP vs BOOT_CONFIG_PROT (and ideally toggle
the boot0 write-protect) so the Balika boot0 edit could be done in software.

[1] mmcsdpub DECODED (the QNX MMCSD publisher)
  - /base/bin/mmcsdpub (23600B, 750 root:nto). "MMCSD publisher" daemon.
  - Usage: -f raw_device, -m pps_path (default "/fs/pps/qnx"), -p insert:removal,
    -e enumerate. Reads DCMD_MMCSD_DEVINFO (devctl), publishes to PPS:
      strings "read_only::true/false", "write_protection::%s", "blocks_size",
      "-partition_count", "-status", "sector_size". It is a MONITOR/publisher,
      NOT a WP toggler. Designed for removable SD cards (hotplug events), not
      eMMC boot partitions.
  - PPS path problem: default "/fs/pps/qnx" does NOT exist; real PPS is "/pps".
    Worked around with: mkdir /pps/qnx + -m /pps/qnx. It then creates
    /pps/qnx/{device,driver,mount} but publishes NO data for boot0 (empty PPS;
    likely waits for a "card inserted: Ready" event that boot0 never sends).
  - Verdict: mmcsdpub is a dead end for reading boot0 WP state.

[2] GROUP WRAPPER MAP (getroot's g_<group> setgid wrappers, all /base/bin)
  - g_<group> for ~400 groups: g_nto, g_Disk_Drivers, g_pps, g_sys, g_rpmb,
    g_trustzone, g_trustzone_users, g_powerauth, g_powerman, g_secconfmgr,
    g_filesystem, g_stp, g_1000*/g_1100*/g_1200*, g_dev0..g_dev99, g_android_*.
  - Each is setgid + procmgr_ability + system("/bin/ksh"). Grants ONE group.
  - mmcsdpub needs BOTH nto (execute) AND pps (PPS). No single wrapper grants
    both; chaining g_nto -> g_pps loses nto. Couldn't combine.

[3] STATUS / THE WALL (final for this session)
  - CONFIRMED: boot0/boot1 write = "Read-only file system" (EROFS) - eMMC boot
    partition write-protect is SET. User area (uda0/os0/dmi0) = writable.
  - The WP is enforced at the eMMC controller level (BOOT_WP power-on, or
    BOOT_CONFIG_PROT permanent). Distinguishing them would need ext_csd read,
    which mmcsdpub can't deliver for boot0. From the running OS, boot0 writes
    are blocked either way (a temporary BOOT_WP is re-set by SBL1 each boot,
    before the OS runs, so there is no OS-reachable window).
  - => Software replication of Balika is BLOCKED at the boot0 write-protect.
     The definitive write path for boot0 remains HARDWARE: ISP test points
     (no desolder) or desolder, exactly as Balika's method required.

[4] WHAT WAS ACHIEVED THIS ARC (7J-7M) - substantial, durable
  1. Raw eMMC READ access via g_Disk_Drivers (software, no hardware).
  2. Full dumps: boot0/boot1/nvram0/dmi0 -> priv-research/classic-emmc/.
  3. Pinned "bbss.insecure" = build-info field8 (u32) @ boot0 offset 0x35a98
     (currently 0=SECURE; nvram0 copy=1=INsecure, a getroot mod_nvram artifact).
  4. Decoded the full imggen unlock toolchain (prototype bootloader + HWI + GPT),
     saved to priv-research/imggen/.
  5. Mapped the write-protect scope (boot0 RO / user area RW) and the group
     wrapper mechanism (g_<group>).
  6. Established that the unlock requires a hardware boot0 write (ISP/desolder).

[5] STRATEGIC CONCLUSION
  - Classic/Passport: the unlock is now FULLY understood and pinned to one byte
    (boot0@0x35a98), but the WRITE is hardware-gated (boot0 WP). Remaining
    routes: ISP test points (the "no desolder" hardware path), or accepting the
    getroot userland root as the ceiling.
  - Priv: unchanged - its nvuser token is NOT hardware-WP'd (unlike boot0), so
    the Priv's equivalent unlock (write hlos_unsigned.tkn to nvuser) is actually
    EASIER to write IF you can reach the raw partition - but the Priv has no
    g_Disk_Drivers equivalent (its getroot is a different family, and its block
    devices are SELinux-gated). The Priv still needs root or ISP.

ARTIFACTS: session7j-7m notes; classic-emmc/*.img; imggen/; mmcsdpub binary.
================================================================================
