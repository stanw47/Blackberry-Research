================================================================================
SESSION 7K - "bbss.insecure" FLAG PINNED (imggen source + live boot0) - 2026-08-30
================================================================================
Goal: pin the EXACT location/meaning of the "bbss.insecure" flag so we know
precisely what to edit to replicate Balika (Classic/Passport unlock).

[1] imggen SOURCE DECODED (github.com/BBAndroids/imggen, public GPL)
  - main.py: input = <boot0 dump> + <user dump>. Finds build info at
    boot0.find("RIM BlackBerry Device") - 0x10, parses 0x4fc bytes.
  - bb.py: _BUILD_INFO_FORMAT = "<II4sI64s16s16s12sII...x22...40s1024s>".
    Field 8 (u32 @ offset 0x7c) = the SECURE flag. `secure = (field8 == 0)`.
    Other fields: version, hwid (0x9700270a for this Classic = "mockingbird/
    ontario"), builder="ec_agent", rev_table, mct (partition map).
  - Files: stage1/2/3.mbn, bbss.mbn, sbl1.mbn, aboot.mbn, rpm.mbn, tz.mbn,
    sdi.mbn, NON-HLOS.bin, boot_gpt_{secure,insecure}.bin (2560B, differ at
    byte 529 = GPT ptable CRC), user_gpt.bin.
  - generate_hwi(): produces a TEXT hwi (product/variant/pcb/pop + FNV1a
    chksum), written into the boot GPT 'hwi' partition.

[2] bbss.mbn = the BBSS component - THE flag semantics (strings)
  - "bbss_insecure"                     <- the flag name
  - "bsi_update bbss_insecure failed"   <- set via BSI (BlackBerry Sec Infra)
  - "insecure device; ignoring SBL auth failure!"  <- WHEN SET: skip SBL auth!
  - "bbss_wp_type"                      <- write-protect type
  - "BB Attestation CA (insecure)" / "BB Root CA (insecure)" - insecure CAs
  => bbss_insecure = "skip SBL signature verification". This is the unlock.

[3] LIVE CONFIRMATION (our Classic dumps) - the flag IS the build-info field8
  boot0.img  : build info @ 0x35a1c, field8 @ 0x35a98 = 0x00000000 = SECURE
  nvram0.img : build info @ 0x1801c, field8 @ 0x18098 = 0x00000001 = INSECURE
  boot1.img  : no "RIM BlackBerry Device" (boot1 is a different SBL1 image)
  => boot0 (which the bootloader reads) says SECURE; nvram0 says INSECURE.
     The nvram0 value is likely a getroot "mod_nvram" artifact (the rootkit
     touched nvram but NOT boot0 -> hence device is still secure-boot).

[4] WHAT THE UNLOCK REQUIRES (now precise)
  1. Set boot0's build-info field8 (u32 @ boot0 offset 0x35a98) to non-zero
     (insecure) - OR let imggen regenerate boot0 from the insecure template.
  2. Write the prototype bootloader chain (stage1/2/3, bbss.mbn, sbl1.mbn,
     aboot.mbn) into boot0/boot1 via imggen.
  3. Reboot -> bbss sees bbss_insecure -> "ignoring SBL auth failure" ->
     prototype aboot -> fastboot -> adb sideload LineageOS.
  All of this needs WRITE access to boot0/boot1.

[5] WRITE ACCESS - the remaining gate
  - /dev/emmc/* is 660 root:Disk_Drivers -> g_Disk_Drivers grants rw at the
    DAC level. But the eMMC boot partition may be hardware write-protected
    (BOOT_WP / "bbss_wp_type"). MUST verify before writing boot0.
  - We ALREADY HAVE full backups: boot0.img + boot1.img (saved), so a
    controlled test is recoverable via re-flash of the dump (IF write works).

[6] NEXT STEPS (ranked, with brick-risk gating)
  1. SAFE write test: write to a NON-critical region first (e.g. dmi0 or a
     spare block on user0) to confirm the group can actually write (not just
     read) at the eMMC level.
  2. Read the boot WP state (ext_csd BOOT_WP / "bbss_wp_type" in bbss.mbn,
     or attempt a single-sector write to boot0 with immediate re-read).
  3. If writable: regenerate boot0 via imggen (or patch field8 @ 0x35a98 ->
     0x00000001) on a COPY, write back, reboot, observe "insecure device".
  4. Then prototype bootloader + LineageOS (balika's build) sideload.

NOTE: This is the Classic/Passport (QNX) unlock, now with the flag pinned to a
specific byte offset (boot0 @ 0x35a98). It does NOT directly unlock the Priv
(different boot chain), but it fully exercises the proven BB10 unlock technique.

ARTIFACTS: /home/stanw47/priv-research/classic-emmc/{boot0,boot1,nvram0,dmi0}.img;
  /tmp/opencode/imggen/ (full toolchain); this note.
================================================================================
