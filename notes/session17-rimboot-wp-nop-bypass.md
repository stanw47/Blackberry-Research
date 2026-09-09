================================================================================
SESSION 17 - RIMBOOT WP-GATE NOP-BYPASS: WRITE ATTEMPTED, CARD STILL REFUSES
================================================================================
2026-09-09, Passport (windermereemea, live). Hardware connect ritual as usual
(blackberry-connect tunnel + paramiko, key auth, root via /base/bin/__root).

--------------------------------------------------------------------------------
[1] MOTIVATION (session16 follow-up)
--------------------------------------------------------------------------------
session16 showed rimboot_update's boot_sector_write_protected() (0x19be) returns
-1 on ext_csd[0xad] bit2, printing "Flash boot regions are permanently locked :
4", aborting BEFORE any write, with -x unable to skip it. Open question: is the
write-path EROFS a real card/driver refusal, or just rimboot's own overcautious
gate? This session answered it: patch the gate out and actually let it write.

--------------------------------------------------------------------------------
[2] THE PATCH (local copy, VA == file offset, flat ELF)
--------------------------------------------------------------------------------
  Original @0x1a7c:  d5 08        bpl 0x1a90   (branch only if bit2 NOT set)
  Patched   @0x1a7c:  e0 08        b   0x1a90   (unconditional -> bit0 test)
  Decision: with BOOT_WP=0x04 (bit2 set, bit0 clear), the bit0 test returns 0
  ("not protected") -> main path 0x114a (nvram_wp + write/verify) is reached.
  Binary kept as rimboot_update_nogate (md5 179c71f5337b3be2278ed49c483c1b76).
  Rootkit note: QNX SH4/Thumb encoding D5xx = bpl, E0xx = b (always).

--------------------------------------------------------------------------------
[3] LIVE RUN (signed windermereemea SFI, -x -f)
--------------------------------------------------------------------------------
  Option Enabled: Force
  BEFORE --> WP : 1 WP_PROGRESS : 1     (nvram_wp() printed; WP bits WERE set)
  AFTER  --> WP : 0 WP_PROGRESS : 0     (tool cleared the NV upgrade flags)
  Writing bootrom (669472 bytes)...
  Verifying bootrom...
  RC=1
  stderr: ERROR : main(321) : Error writing to bootrom area : Read-only file system
  stderr: ERROR : main(362) : ERROR: BOOTROM WRITE FAILED, BUT ORIGINAL BOOTROM
          IS STILL INTACT                                                   (!!)
  (RC captured correctly this time: echo RC=$?, no backslash escape bug.)

--------------------------------------------------------------------------------
[4] CONCLUSION
--------------------------------------------------------------------------------
* The WP gate was NOT the only lock. Even with it bypassed and nvram_wp() run,
  the actual write to /dev/emmc/boot0 fails with EROFS (errno 30) at the
  driver level -- the BB sdmmc driver refuses R/W open of the write-protected
  boot0 (same policy observed in session9a). Original bootrom intact, no harm.
* rimboot_update alone can never write boot0 while card/driver WP is armed.
  Confirms session9 "no software route via native devctl" picture; the missing
  primitive is still a raw CMD6 SWITCH to clear ext_csd[0xad], unavailable in
  the stock driver (no VUC/ANY handler, session9/10a).
* NEW datum: NV WP/WP_PROGRESS were BOTH 1 before this run (leftover from the
  session16 manual bits-42/43 arming) and the tool's nvram_wp() cleared them.
  So our earlier "negative" NV test may have targeted the right NV block but
  rimboot's own nvram_wp() is what manages WP <-> WP_PROGRESS transitions.

--------------------------------------------------------------------------------
[5] NEXT EXPERIMENT (candidate, needs user OK: intentional reboot + NV churn)
--------------------------------------------------------------------------------
Force rimboot's r0==1 branch (patch cmp/beq so it always takes the "power-on
protected" path 0x110a): prints "removing boot sector write protection", sets
NVRAM bits via nvram_wp(1), asks for power-cycle (Oleksandr flow). Then:
power-cycle the device, re-read ext_csd[0xad]. If it drops to 0 -> the WP was
NV-driver-controlled and the next -x -f run writes cleanly. If still 0x04 ->
bit2 is a genuine card fuse -> hardware route only (desolder or bblink EDL).

Alternative (no reboot): write = patch rimboot_update to target /dev/emmc/boot1
(string "boot0" -> "boot1", same length) and verify ACK/DIG proof that the SAME
binary + write path works when the boot partition is not WP'd (boot1 opens
O_RDWR). Content identical signed bootrom; device keeps booting boot0. Pure
write-path proof, zero risk.

--------------------------------------------------------------------------------
[6] ARTIFACTS
--------------------------------------------------------------------------------
  /tmp/opencode/rimboot_update_nogate        (patched binary, md5 above)
  /tmp/opencode/run_nogate.py                (paramiko runner; RC capture fixed)
  on device: /accounts/1000/shared/documents/{rimboot_update_nogate,
             BR-windermereemea.signed.sfi, probe_extcsd.py}
================================================================================