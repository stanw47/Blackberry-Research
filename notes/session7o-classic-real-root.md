================================================================================
SESSION 7O - CLASSIC REAL UID-0 ROOT ACHIEVED - 2026-08-30
================================================================================
RESULT: Real interactive uid-0 root obtained on the Classic via the
"btool pathtrust whitelist" trick. This closes the gap that the earlier logs
flagged ("NO interactive uid-0 reachable for devuser").

[1] THE METHOD (confirmed end-to-end)
  - getroot's root payload is btool (a sh script), reachable via the
    /base/scripts/ota_info_pps.sh symlink, and it runs AS ROOT at boot
    (autoroot) and on switchzone.
  - btool whitelists files with: /proc/boot/pathtrust !<path>
  - Added "/proc/boot/pathtrust !/base/bin/__root" to btool at LINE 31 (right
    after the mod_nvram whitelist). First attempt put it at the very end (after
    the Term49 install), which was never reached.
  - On reboot, autoroot ran btool -> __root became "trusted" -> its suid works.
  - VERIFIED: __root wrote to /root/ (WRITE OK), listed /root/, no more
    "Operation not permitted".

[2] MECHANICS
  - /proc/boot/pathtrust (root:nto 750): '<file>'=trust FS, '!<file>'=trust file,
    '-t <file>'=query, 'lockdown'. Needs ROOT to change (nto -> "failed: 1").
  - Trust list re-applied every btool run (boot autoroot + switchzone); not
    persistent by itself.
  - switchzone (via __upd): os:true SWITCHES the OS SLOT (drops dev-mode+SSH);
    os:false does NOT run btool. Only safe btool trigger = boot autoroot.

[3] WRITE-PROTECT AS ROOT (definitive)
  - boot0/boot1: EROFS (HARDWARE BOOT_WP, controller-level - uid-0 does NOT
    help). rpmb0: authenticated-only. os0/uda0/dmi0/os1: WRITABLE (user area).

[4] IMPLICATIONS / NEXT
  - Root now: interactive uid-0, full eMMC read (dumps in classic-emmc/),
    os0 writable.
  - "bbss.insecure" flag pinned: build-info field8 @ boot0 offset 0x35a98.
  - To unlock (LineageOS): (1) PathTrust full unlock (public), (2) MMC driver
    patch sdmmc.zip (private/Patreon) -> toggle BOOT_WP -> write boot0@0x35a98=1
    + prototype bootloader (imggen) -> LineageOS.

ARTIFACTS: classic-research-log.txt section 9 (updated); priv-research-log.txt
  section 22 (updated, flash+local synced); dumps in classic-emmc/; imggen/,
  passport_stage3/ in priv-research/.
================================================================================
