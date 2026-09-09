================================================================================
SESSION 19 - DRIVER GATE 0xF182 DECODE, WP HANDLER 0x108D0, PER-NODE EXT MODEL,
              CID LIVE-READ, EXT_CSD NO-CACHE, PASSPORT BOOT0/BOOT1/OS0 DUMPS
================================================================================
2026-09-09, Passport (windermereemea, live via SSH+root until reboot into
red-blink). Hardware connect: blackberry-connect tunnel + paramiko, key auth,
root via /base/bin/__root. Module base 0x100d3000 (this boot). g_Disk_Drivers
group wrapper + __root for dd on /proc/as and block nodes.

-------------------------------------------------------------------------------
[1] MODULE BASE / DRIVER MAP
-------------------------------------------------------------------------------
- devb-sdmmc-rim-msmsdcc base: 0x100d3000 (file), runtime 0x100d3000
  (no ASLR observed across boots).
- .text: 0x100d3000..0x100eb8a0, .data: 0x100eb8a0..0x100ee678
- Gate runtime = fileoff 0xf182 + base = 0x100e2182 (Thumb-2)
- Dispatcher runtime = fileoff 0xe340 + base = 0x100e1340
- WP handler runtime = fileoff 0x108d0 + base = 0x100e38d0
- mmc_switch worker = fileoff 0x100d4 + base = 0x100e0bd4
- Mode table (action->mmc_switch value) at 0x16996+0xbc:
    0->0x1d, 1->0x1c (BOOT_WP), 2->0x1e, 3->0x1f

All addresses verified by re-dumping /proc/1286155/as with correct dd
skip math (skip = addr>>12). Missing module data page 0x100ee000..0x100ef000
dumped as m1page.bin (skip 65774). Previous bad skips (66094) gave "Server
fault on msg pass".

-------------------------------------------------------------------------------
[2] GATE 0xF182 — EXACT THUMB-2 DECODE
-------------------------------------------------------------------------------
Gate is the common entry for DCMD_MMCSD_WRITE_PROTECT (0xC0201A11) and
likely other write-paths. Called with r0=ctp (open context), r1=msg (devctl
message buffer). Logic (capstone, CS_MODE_THUMB):

    r6 = [r0, #8]           ; ext = [ctx+8]  (per-open context pointer)
    r3 = [r6, #4]           ; load [ext+4]
    lsls r3, #31            ; test bit0
    bmi 0xf116              ; if clear -> error 0x13 (ctp,msg,0x13)
    r0 = #1                 ; bit0 ok -> provisional success
    r3 = [r1, #10]          ; idx byte 0 = msg[0xa]
    r2 = #0x2c8
    muls r3, r6, r3         ; r3 = msg[0xa] * 0x2c8  (target stride)
    r1 = [r4, #11]          ; idx byte 1 = msg[0xb]
    r3 = 0x58
    mul  r6, r1, r3         ; r6 = msg[0xb] * 0x58   (lun stride)
    r6 = r6 + r3            ; idx = target*0x2c8 + lun*0x58
    r6 = r6 + r5            ; r5 = ext + 0x1d0 (slot base)
    r3 = [r6, #0x28]        ; load [ext + idx + 0x1d0 + 0x28] == [ext + idx + 0x1f8]
    cbnz r3, ok             ; if nonzero -> gate passes (r0=1)
    else -> 0xf116(ctp,msg,6)

Summary: gate returns success (r0=1) IFF:
  (1) [ext+4].bit0 == 1  (global "WP allowed" flag in ext)
  (2) [ext + idx + 0x1f8] != 0  (slot "attached" flag for target/lun)

idx = msg[0xa] * 0x2c8 + msg[0xb] * 0x58, where msg[0xa]/[0xb] are bytes
10/11 of the *devctl message header*, not our payload.

-------------------------------------------------------------------------------
[3] WP HANDLER 0x108D0 — EXACT DECODE
-------------------------------------------------------------------------------
Dispatch entry for 0xC0201A11. r0=ctp, r1=msg. Logic:

    r8 = [r0, #8]           ; ext = [ctx+8]
    r5 = [r1, #0x30]        ; payload ptr (our packed struct)
    ; idx computed identically (msg[0xa]*0x2c8 + msg[0xb]*0x58) -> r6 = ext + idx + 0x1d0
    fp = [r6, #0x20]        ; fp = [slot+0x20] = [ext+idx+0x1f0]
    r2 = [r6, #0x28]        ; r2 = [slot+0x28] = [ext+idx+0x1f8] (same flag gate checks)
    bl  gate (0xf182)
    cmp r0, #1; bne -> error path (0x10984)
    ldrh r2, [r8, #0x24]    ; [ext+0x24] as u16
    cmp r2, #1; bne -> error 0x30
    worker 0x100d4 called with:
      r1 = mode table byte (from 0x16996+0xbc via payload mode)
      r2 = [r6, #4]         ; [slot+4] = [ext+idx+0x1d4]
      r3 = [r5, #4]         ; payload mode field

Summary: worker reached IFF gate passes AND [ext+0x24] == 1 (u16). The worker
r1 selects mmc_switch value: mode 0->0x1d, 1(BOOT_WP)->0x1c, 2->0x1e, 3->0x1f.

-------------------------------------------------------------------------------
[4] PER-NODE EXT MODEL (CRITICAL FINDING)
-------------------------------------------------------------------------------
Our WRITE_PROTECT payload is struct.pack('<IIQQQ', action,mode,lba,nlba,0) (32B):
  lba at offset 8, nlba at 16. With lba=0 -> payload bytes[0xa]=0, [0xb]=0.
The devctl message header places the *same* bytes at msg[0xa]/[0xb] for *both*
/dev/emmc/user0 and /dev/emmc/boot1 probes. So idx = 0 for both.

Yet: user0 WRITE_PROTECT succeeds (rc=0), boot1 returns EIO (rc=5).

Therefore the differentiating state is NOT the index — it is the `ext` pointer
itself: each device node open gets its own `ctx` with a distinct `ext = [ctx+8]`.
- user0's ext: [ext+4].bit0=1 AND [ext+0x1f8]!=0  (slot 0 attached)
- boot1's ext: either [ext+4].bit0=0 OR [ext+0x1f8]==0  (slot 0 NOT attached)

Implication: the "slot attached" flags are per-open-node, not a single global
ext with per-target/lun indexing via header bytes. The header bytes may
encode target/lun per-open at open() time, but the observed behavior with
idx=0 for both nodes and different outcomes proves ext differs per node.

-------------------------------------------------------------------------------
[5] CID — LIVE READ, NO CACHE
-------------------------------------------------------------------------------
probe_cid_hex.py (pushed to /accounts/1000/shared/misc/) issued
DCMD_MMCSD_CARD_REGISTER (0xC0181A14, type=1) on /dev/emmc/boot0,
/dev/emmc/boot1, /dev/emmc/user0. All returned identical 16-byte CID:

    00 91 b2 63 55 93 00 34 45 47 32 33 30 00 01 11

Full 16-byte pattern scan across ALL dumps (heap1/2, m1/m2/m3/m1page, an0..an6)
= 0 hits. CID is read live from the card on every CARD_REGISTER call, not
cached in RAM.

-------------------------------------------------------------------------------
[6] EXT_CSD — NO 512-BYTE CACHE ANYWHERE
-------------------------------------------------------------------------------
- Exact 512-byte signature scan (BOOT_WP[173]=0x04, BOOT_SIZE_MULTI[226]=0x20)
  + structural anchor scan ([0xAA]=00, [0xAD]=04, [0xAE]=0A) across ALL dumps:
    heap1, heap2, m1.bin, m2.bin, m3all.bin, m1page.bin, an0..an6.bin
  -> 0 hits. No full ext_csd copy cached in any writable region.

- One false positive in m3all.bin at 0x101bd208: repeating 0x20-stride pool
  pattern (40 57 27 79 13 00 00 00 21 00 00 02 00 XX 0A DD...), not ext_csd.

- Live anchor for this unit: [0xAA]=0x00, [0xAD]=0x04, [0xAE]=0x0A,
  [0xB3]=0x48, BOOT_SIZE_MULTI[226]=0x20.

-------------------------------------------------------------------------------
[7] COMPLETE WRITABLE ANON SPANS — ALL DUMPED & SCANNED
-------------------------------------------------------------------------------
Region list from /proc/1286155/maps (3806 rows, header skipped). All
writable anon (paddr=0xffffffffffffffff) spans dumped via dd on /proc/as:

  an0: 0x0f286000..0x0f301000 (123 pg)
  an1: 0x0fb22000..0x0fb41000 (31 pg)
  an2: 0x0fff6000..0x0fffd000 (7 pg)
  an3: 0x1001a000..0x10021000 (7 pg)
  an4: 0x10025000..0x10044000 (31 pg)
  an5: 0x10092000..0x100b1000 (31 pg)
  an6: 0x100c6000..0x100c9000 (3 pg)

Total ~200 pages, all scanned for ext_csd (sig + anchor) and CID -> 0 hits.
libc.so.3 {bss} at 0x01101000..0x01106000 is the only other writable mapping
(paddr != -1), irrelevant to driver structures.

-------------------------------------------------------------------------------
[8] PASSPORT BOOT PARTITION DUMPS (NEW ARTIFACTS)
-------------------------------------------------------------------------------
dd under __root from block nodes (all readable, write is EROFS on boot1):

- boot0 (4 MiB): dd if=/dev/emmc/boot0 of=/tmp/bb0_full.bin bs=512 count=8192
  SHA256: 75108c669a25444ed852ca087997788845976e23c7da2a413b42ba77349b34bd
  Content: 1 MB nonzero (0x0..0x100000) = SBL1.
    - EFI PART sig at 0x200, GPT header rev/num garbled (custom minimal).
    - Single GPT entry at LBA 2: "BootROM" first=34, last=511 (478 sectors).
    - SBL1 strings: "Build info: %d.%d.%d.%d, %s, %s, %s",
      "Loading SBL image", "SBL1 decompression failed!", "Jump to SBL1",
      "Preload images build info: %s, %s, %s",
      "DDR training occurred, must reset".
    - ELF magic at 0x4f9e8, 0x56e41, 0x757e9 (probable ELF images inside).

- boot1 (4 MiB): dd if=/dev/emmc/boot1 of=/tmp/bb1_full.bin bs=512 count=8192
  SHA256: bb9f8df61474d25e71fa00722318cd387396ca1736605e1248821cc0de3d3af8
  Content: essentially blank (all zeros, 4 KB nonzero noise only). No SBL.

- os0 first 8 MiB: dd if=/dev/emmc/os0 of=/tmp/os0_8M.bin bs=1M count=8
  SHA256: 429beab37931b853c0e07af712b158e903ec0fc4cfee01d227eb344e751211c9
  Content: QNX v1.2b Boot Loader at 0x0; IFS startup code at ~0x25c594
    ("STACK USAGE", "board_smp_start"), $OS table at 0x386d10,
    SFI markers at 0x25deb1 / 0x7b6f04.

- user0 head (256 KiB) and os0 head (256 KiB) also captured.

These are the first live Passport boot partition dumps in this repo. boot0
contains the SBL1; boot1 is empty; os0 holds the QNX IFS.

-------------------------------------------------------------------------------
[9] DEVICE STATE / RED-BLINK NOTE
-------------------------------------------------------------------------------
After completing all reads (no writes performed), the device was rebooted.
It reached "Finalizing startup..." then shut off and rebooted into the
familiar red-blink (security-boot failure). This is the documented stub/
payload mismatch (README finding #12): the RAM-loader stub injects state
that Windows cap.exe satisfies but bb10mt (and any raw OS flash) does not.
Recovery path: EDL lane (tools/bblink.py + tools/listen_flash.py) on a live
device, or the desolder/ISP route.

-------------------------------------------------------------------------------
[10] ARTIFACTS (LOCAL /tmp/opencode, TO BE ADDED TO REPO)
-------------------------------------------------------------------------------
- bb0_full.bin (4194304 B)  — Passport boot0 SBL
- bb1_full.bin (4194304 B)  — Passport boot1 (blank)
- bb0_head.bin (65536 B)    — boot0 first 64 KiB
- bb1_head.bin (65536 B)    — boot1 first 64 KiB
- os0_8M.bin  (8388608 B)   — os0 first 8 MiB
- os0_head.bin (65536 B)    — os0 first 64 KiB
- u0_sb.bin   (524288 B)    — user0 first 256 KiB
- o0_meta.bin (524288 B)    — os0 metadata region (2nd 256 KiB)
- m1page.bin  (4096 B)      — module .data page 0x100ee000
- capture_boot.py           — dump script
- probe_cid_hex.py          — CID probe script
- deliverables_oleksandr.md — summary of extracted dumps (local reference)

-------------------------------------------------------------------------------
[11] REPO IMPACT
-------------------------------------------------------------------------------
- New session note: this file.
- New artifacts under dumps/ (or a passport/ subdir) for the Passport dumps.
- README updates: gate decode (#2, #3), per-node ext model (#4), CID live-read
  (#5), ext_csd no-cache (#6), boot0 SBL layout (#8), complete writable region
  coverage (#7).
- Existing dumps/ dir is Classic-only; recommend adding passport/ subdir or
  renaming to passport_dumps/ to avoid confusion.

================================================================================