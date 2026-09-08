# session14 - EDL gate test hits security wipe; cs-olapi NVRAM unlock lane

## What happened (Classic, EDL marker gate test)
- Built `gate_plug_and_test.py`: fused "wait for VID 0x0FCA -> immediately
  bring-up" runner (device only stays in BootROM a few seconds after plug-in).
- Fixed bblink bug: `d.claim_interface()` -> `usb.util.claim_interface(d, iface)`
  (previous pyusb API assumption broke EVERY open at the claim step).
- Added `BBSession.session_reboot()` = Channel0(cmd=3) mirroring bb10mt
  `TBBUSB.Reboot`; used to drop an OS-session PID 0x8017 device down to BootROM.
- Learned PID map (bb10mt `ConnectToBB`): 1 = BootROM, 0x8001 = RAM-loader,
  0x8017 = normal OS session (needs session_reboot first).
- Result: reached `model_id 9700270A` (RAM-loader target 0x9700270a confirmed on
  the actual Classic), set Mode(1) ok, then **device dropped during
  password_info exchange -> device initiated a SECURITY WIPE**.

## Key facts
- BootROM handshake order (bb10mt ramloader.ConnectToBB):
  Open([1,0x8001]) -> Ping0 -> GetVar(2,2000) [modelID@FBRomInfo[ 0x14 ] of
  buffer] -> SetMode(1) -> PasswordInfo -> SwitchChannel -> GetMetrics ->
  LoadLoader -> SendAndRunLoader -> WaitForLoaderMode(PID 0x8001) ->
  InitializeLoaderInterface.
- `Channel0(var cmd, data)` : reply echo updates cmd; resp[0]=rsp cmd, resp[1]=mode.
- HashPassV2 (ucrypto.pas) == our `hash_pass_v2` byte-for-byte.
- PasswordInfo: cmd 0x0A -> 0x0E (challenge@[4:8], salt@[12:20], iters=LE@[20:24])
  -> hash + prefix `00 00 40 00` -> cmd 0x0F -> 0x10 done (+ drain read).
- **Wipe on failed handshake**: a failed/incomplete BootROM password exchange
  triggers a full device security wipe. On the Classic test unit this is only a
  re-root; on the Passport it is an unacceptable risk. => EDL raw writing stays
  gated; do NOT retry EDL until the exchange is proven or an OS lane works.

## cs-olapi / "oleksandr" NVRAM unlock (NEW LEAD, credited source)
"If you really have B_PWR_WP_EN set, try the unlock method that uses the
official RIM updater. Set bits 42 and 43 in block 0x2019 of the NVRAM."
  - Reference routine (`nvram_wp`, called FUN_00011fa0 by source): open64
    `/dev/nvram` O_RDWR, pread64(fd, buf, 0x80, 0x2019). NV_OSSTORE_BitFlags
    record. Writeback portion not provided directly but implied.
  - Interpretation: OS/driver consults NV OSSTORE bit flags to decide whether
    the eMMC BOOT partitions may be written; official RIM updater (autoloader
    flashing SBL) clears/uses these to allow boot0 writes. If we reproduce it
    from the rooted OS, boot0 becomes writable WITHOUT EDL or desolder -> the
    simple OS-lane return (g_Disk_Drivers) becomes viable again.
  - Bit map if LSB-first and flags at record[0]: bits 42/43 -> record[5] bits
    0x04|0x08 = 0x0C. UNCONFIRMED: need live record + full function to know
    the exact flag base / endianness.
- nvram0.img: the record predated as possibly nvram0 offset 0x18000+0x2019 =
  0x1A019 (has 'NVRE'@+4) OR raw slot at 0x100C80; both inconclusive offline.
  The DEVICE (/dev/nvram:0x2019) is the authoritative view - inspect on-device.

## Artifacts
- `gate_plug_and_test.py` (fused EDL marker test, auto session-reboot)
- `nvram_bits.py` (inspect/set/clear/backup the NVOSSTORE bitflag record)
- bblink.py: claim fix + session_reboot()
- [in session5+] initial LDR_B loader upload (2024-byte chunks, addr = model
  load addr) verified; RAM-loader password flow matched to bb10mt.

## Next move
1. Let the Classic finish the security wipe; then boot it to OS.
2. Confirm state (still rooted? if wiped, re-root via the established Windows
   flow) and handshake back to USB PID 0x8017 OS session.
3. On-device: `nvram_bits.py inspect` (reads /dev/nvram:0x2019). Cross-check
   vs nvram0.img; identify the REAL flag base. Confirm bits 42/43 meaning.
4. `nvram_bits.py backup` then `set`; reboot; test OS-side boot0 write via
   `/dev/emmc/boot0` (root, g_Disk_Drivers) - does "Operation not permitted"
   disappear? This is the oleksandr unlock test.
5. If OS-lane unlock works: use it for the Passport boot0 + user partition
   (no EDL bombs). If not: fix the EDL password exchange deterministically
   (mirror bb10mt exactly, dry-run on a spare) before ANY further EDL attempt.
## Update (same session, continued)
- Resident 0x8001 "Reload OS" loader ignores bb10mt protocol entirely (channel0
  ping0/set_mode(2)/reboot all timeout at 8s). It talks the official-updater
  protocol, NOT the bb10mt RAM-loader channel set. => cannot be driven by our
  tooling; cannot even drive it to reboot into BootROM from USB.
- Power-off + plug-in ritual DOES NOT reproduce BootROM PID 0x0001 on the wiped
  device: SBL2 now boots straight into the 0010 "Reload OS" loader (0x8001).
  BootROM requires either a working OS stack or the official toolchain. The
  earlier archive/ session that saw PID 0x0001 was with the OS intact.
- WIPE-LOOP: the 0010 loader re-runs the security wipe whenever the USB host
  drops/errors (observed twice: after our failed handshake, and again after
  host disconnect). With OS gone it just keeps erasing. Boot0 survival after
  repeated wipes UNCONFIRMED - do not keep poking this state.
- DECISION: STOP EDL/BootROM experiments on the Classic. The EDL lane's failure
  mode (full secure wipe) is not tolerable even on the test unit now that the
  OS is gone and BootROM entry is lost.
- PIVOT to OS lane (oleksandr NVRAM bits 42/43): restore rooted OS via the
  proven Windows autoloader, then on-device inspect/set the NV OSSTORE bit
  flags and test OS-side boot0 writability. No EDL involved.
