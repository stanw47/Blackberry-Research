================================================================================
SESSION 8A - GROUP-WRAPPER PRIV-ESC + LIVE MMC DEVCITL CHANNEL (BREAKTHROUGH)
2026-09-02  (follows 7j/7r/7w/7y; cross-ref notes/session7w-connect-ritual.md)
================================================================================

[1] THE PRIVILEGE-ELEVATION PRIMITIVE (setgid group wrapper)
  - /base/bin contains ~200 setgid symlink-family "group wrappers":
        __USER   (setuid-user)   g_GROUP (setgid-group)   u_USER (setuid-user)
    ALL are the SAME 4488-byte ELF32-ARM binary, differing ONLY by filename;
    the target uid/gid is DECODED FROM argv[0] (the filename). Byte-identical
    BuildID 84c92d436dc1ffd7c62c27eccfadb2f0.
  - Owner root, group = the target group, perms -rwxrwsrwx (SETGID bit).
  - RE (capstone, Ghidra): main() = getuid/getgid/getpid/geteuid/getegid,
    then procmgr_ability() per ability, setregid(egid=target, rgid=-1),
    setreuid, then system("/bin/ksh"). argv[] is ONLY used to decode the group;
    the command it runs is a FIXED "/bin/ksh" (NOT argv-injectable).
  - USAGE: pipe commands into its STDIN. It spawns a ksh (or execs) with the
    target group as effective gid, e.g.:
        echo "id;groups" | /base/bin/g_Disk_Drivers
        uid=100(devuser) gid=132(Disk_Drivers) groups=132(Disk_Drivers)
  - To run arbitrary code under the group: exec python from within the ksh:
        echo "exec /accounts/1000/shared/misc/berrycore/bin/python3.11 /path/py" \
            | /base/bin/g_Disk_Drivers
        -> the python process runs with egid=Disk_Drivers.

[2] CONFIRMED: /dev/emmc NOW OPENS UNDER Disk_Drivers
  - pidor: /dev/emmc/* = brw root:Disk_Drivers 660.
  - Previously EPERM for devuser. Under g_Disk_Drivers (egid=132): open O_RDWR
    of /dev/emmc/boot0 SUCCEEDS (fd). DAC gate removed.

[3] LIVE DEVCITL CHANNEL INTO sdmmc-rim-msmsdcc (pid 741404) - VERIFIED
  Sending raw devctl from the elevated (Disk_Drivers) process to /dev/emmc:
    dcmd                     result
    DCMD_MMCSD_CARD_REGISTER 0xc0181a14 -> ret 0  (success)
    CID read  (0x40101a44)  -> ret 0  (writes 16B CID out at buf+0x30)
    ext_csd read (0x40011a46, byte 0xa8) -> ret 0
    DMMC WRITE_PROTECT       0xc0201a11 -> ret 5  (EIO: reached handler, WP op)
    DMMC ERASE               0xc0201a13 -> ret 22 (EINVAL)
  => The group gate was THE only blocker; channel is live and reaches handlers.

[4] WRITE_PROTECT -> BOOT_WP PATH (RE, file offsets in devb-sdmmc-rim-msmsdcc)
  devctl (0xc0201a11) -> 0xfcec handler -> bl 0xf48c core -> mmc_switch 0x76c0.
  Devctl buffer layout (mmcsd_devctl_s): target@0x0a, lun@0x0b, wp struct @0x30:
    action@0x30, mode@0x34, sd_off@0x38, sd_nlba@0x3c,
    start(64)@0x40, nlba(64)@0x48.
  Routing in 0xf48c:
    sl gate: cmp sl,#0x1c ; bne 0xf5c2 (else broad path)
    0xf524 ands r5,r5,#7  -> 0 => USER_WP (mmc_switch index 0xab=171)
      0xf52a cmp r5,#2 (==2) => BOOT_WP (mmc_switch index 0xad=173, value=r7)
    mmc_switch 0x76c0: (r0=hba, r1=flgs=1, r2=<cmdset/3>, r3=index, [sp]=value)
    -> 0x8240 = actual CMD6 SWITCH send.
  sl (the gate value) = handler's sb = action-to-table byte:
        action 0->0x30, 1->0x43, 2->0xf0, 3->0x08   (table @0x63a0+0xd9+action)
    NO action equals 0x1c => the BOOT_WP mmc_switch branch is UNREACHABLE via
    normal WRITE_PROTECT action values 0..3. (confirms 7r ["sl==0x1c gate"]).
  r5 (=router USER/BW) = core r2 = [partition-tbl].  Segmented per-partition.

[5] CONCLUSION / NEXT
  - devctl BOOT_WP route is gated (sl==0x1c) and, without patching R/O
    code/rodata, NOT reachable through action values 0..3.
  - Live channel (CARD_REGISTER/CID/ext_csd read) is confirmed working under
    Disk_Drivers -> we have a reliable devctl path to the driver for reads.
  - To CLEAR ext_csd[173] B_PWR_WP_EN (boot-partition WP) the remaining option
    is session7r Option 2: drive mmc_switch(0x76c0)(hba,1,3,173,0) directly,
    via a memory patch / thunk in the driver's writable region using the
    known-good /proc/741404/as R/W primitive.
================================================================================
