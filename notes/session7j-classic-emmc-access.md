================================================================================
SESSION 7J - CLASSIC RAW eMMC ACCESS ACHIEVED (no desolder) - 2026-08-29/30
================================================================================
GOAL: replicate Balika's bootloader-unlock method WITHOUT eMMC removal, by
getting raw eMMC access from the already-rooted Classic over dev-SSH.

[1] THE WIN - g_Disk_Drivers = raw eMMC access (software, no hardware)
  - The getroot rootkit installed a family of setgid "group wrappers" in
    /base/bin: g_<groupname> for EVERY group (g_nto, g_Disk_Drivers, g_sshd,
    g_1000_*, ...). Each is the SAME 4488-byte binary, setgid to its group.
  - RE of the binary (g_Disk_Drivers): main() builds a procmgr_ability() message
    (gains a QNX process ability), setuid/setgid/setregid/setreuid to the group,
    then system("/bin/ksh"). It does NOT exec argv - it spawns an INTERACTIVE
    ksh with the target group. Usage: pipe commands into its STDIN.
  - /dev/emmc/* is owned root:Disk_Drivers (brw-rw---- = 660). So g_Disk_Drivers
    grants READ+WRITE to the raw eMMC.

[2] FULL eMMC LAYOUT (Classic, QNX) - exposed under /dev/emmc/
  boot0, boot1 (4MB each - the SBL1/boot code), boot0.01000000-.../02000000-...
  (sub-regions), rpmb0, nvram0 (4MB), cal_work0, dmi0, user0, os0/os1 (OS),
  uda0 (user data), radio0 (modem), sd0 (SD). hd0-hd7 are symlinks to these.

[3] DUMPS OBTAINED (saved to /home/stanw47/priv-research/classic-emmc/)
  - boot0.img  (4,194,304 B)  md5 d6a15e39... = Qualcomm SBL1 (secboot3,
    msm8960). Source paths embedded: /mnt/data/mstuglik_l/e7_boot/boot_images/
    1.0.x/core/boot/secboot3/{msm8960/sbl1,common}/...  Strings: "HWID: 0x%x",
    "QFPROM FuseData/FuseMap", "BOOT_WP", "BOOT_CONFIG_PROT", "rim_sbi_init",
    "AFAB_M2VMT_M2VMR0_0" (board id), tzbsp_pil_unlock_area / tzbsp_blow_sw_fuse.
  - boot1.img  (4,194,304 B)  md5 b5cfa9d6... = same SBL1, slightly different.
  - nvram0.img (4,128,768 B)  = NVRE records + "RIM BlackBerry Device" +
    "ec_agent" + BB10/QNX partition map (nvram, cal_work, cal_backup, dmi_mbr/
    sig/fsys, os_mbr/sig/fsys, system, radio, user) + system logs.
  - dmi0.img   (1,048,576 B)  = DMI (device/board info region).

[4] WHAT THIS ENABLES
  - READ (CONFIRMED) of the entire eMMC incl. boot0/boot1/HWI/nvram. This is
    the "access eMMC without removal" goal, achieved via SOFTWARE (rootkit group
    wrapper), not hardware (desolder/ISP).
  - WRITE: TBD. The block devices are 660 root:Disk_Drivers -> the group has
    write permission at the DAC level. Whether the eMMC hardware accepts boot0
    writes depends on BOOT_WP (boot write-protect) - the SBL1 has "BOOT_WP" /
    "BOOT_CONFIG_PROT" strings. MUST check ext_csd/BOOT_WP before attempting
    any boot0 write (brick risk).
  - To replicate Balika: locate the HWI / "bbss.insecure" flag in boot0 (or a
    config region), set it, write back. The authoritative reference is the
    BBAndroids/imggen source (boot_gpt_insecure.bin vs secure) + passport_stage3.

[5] NEXT STEPS (ranked)
  1. Read BBAndroids/imggen source to learn the EXACT "bbss.insecure" location
     and the boot0/HWI edit it performs (github.com/BBAndroids/imggen, public).
  2. Determine the eMMC boot-partition write-protect state (ext_csd BOOT_WP /
     "BOOT_CONFIG_PROT") WITHOUT writing to boot0.
  3. If boot0 is software-writable: replicate the imggen edit on a COPY, verify,
     then (with user consent) write back and test the unlock -> LineageOS path.
  4. Cross-reference: does the Priv have the SAME group-wrapper trick? (Priv
     getroot/rootkit is a different family; but the Priv's nvuser is SELinux-
     gated, not group-gated - this Classic trick does not directly transfer.)
  NOTE: this is the Classic/Passport (QNX) path. It does NOT unlock the Priv,
  but it is the proven Balika method made non-destructive, and it exercises the
  exact technique (HWI/bbss.insecure edit) that the whole BB10 unlock family
  relies on.

ARTIFACTS: /home/stanw47/priv-research/classic-emmc/{boot0,boot1,nvram0,dmi0}.img
  + g_Disk_Drivers/__root/g_nto binaries in /tmp/pp/.
================================================================================
