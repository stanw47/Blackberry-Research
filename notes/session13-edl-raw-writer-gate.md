===============================================================================
SESSION 13 - RAW EDL WRITER + THE GATE TEST (no-desolder decision point)
===============================================================================
2026-09-07. Built the raw BootROM/RAM-loader USB tool and the boot0-marker
gate test. This decides whether the no-desolder Passport->Android conversion is
physically possible on the original eMMC chip.

[0] WHAT WE LEARNED FROM bb10mt SOURCE (now cloned: priv-research/bb10mt-src)
  - Full protocol ported to Python (tools/bblink.py):
      * Channel0/1/2 framing exactly as bbusb.pas
      * FPC crc32 variant: reflected poly 0xEDB88320, init as passed (0 for
        bb10mt), NO final xor. Cross-checked: crc32(0,'123456789')=0x2DFD2D88;
        PKZIP-ized (=init FFFFFFFF, final xor) matches zlib 0xCBF43926.
      * BootROM bring-up: Ping0($14\x05\x83\x19), GetVar(2,2000)=BR metrics
        (modelID @16), SetMode(1 "RIM-BootLoader"), PasswordInfo ($0A/$0E/$10
        exchange, HashPassV2 = PBKDF-style SHA-512 loop), SwitchChannel([6,6]),
        GetMetrics, SendLoader(WRITE_RAM_SETUP $F009 + $F004 chunks + $F00A VERIFY,
        chunk 2024 for Qualcomm), RunLoader($F005), wait PID 0x8001, SetMode(2
        "RIM-RAMLoader"), PasswordInfo again.
  - RAM-loader Channel2 command set (bbloader.pas):
        $20EE PreFlash (resp $39; data[0]=$15 Classic / $40 Passport)
        $B4   FlashRegionsInfo (resp $D2; Blocks @12, user KB @88)
        $D9   GetMCT ($C9)  $E7 PIN ($D1)  $EA BSN ($FC)  $DB VendorID ($CB)
        $BF   DRAMInfo ($D9)  $D8 OSMetrics ($C8)
        $F7   SendBlock -> resp $DF   [u32 block#][u32 len][data]
        $40F9 SendSignature [u16 560][560B] -> resp $4006
        $40C0 Complete -> resp $4006
        $80EF Reboot -> $80C7
  - RAM-loader firmware ALSO exposes raw commands (from loaders RE, see
    priv-research/bb10root-tools/ramloadercommands.txt):
        $E4 CREAD INIT,  $E5 CREAD [00][u32 addr][u32 size<=0x3FA0]  (raw read)
        $EE ERASE_SECTOR,  $DE BOOT_MODE,  $F8 Write,  $DC DO_CRC_VERIFY,
        $C4 READVERIFY [00][addr][size][val],  $D5 SUPER_NUKE, $D7 SetActiveMCT

[1] THE HARDWARE GATE (only unknown left)
  - OS-side boot0 write is dead: g_Disk_Drivers gives DAC write permission but
    the eMMC controller + SBL1 block it (session7j/9/11: "Operation not
    permitted", ext_csd BOOT_CONFIG_PROT / BOOT_WP). Verified on Classic.
  - Question: does the EDL RAM-loader, running pre-SBL1, write into the
    HARDWARE BOOT0 partition (blocks 0-31) or only the user-area mapping?
    bb10mt NEVER touches boot0 (OS/radio land in user area). The raw CREAD/
    BOOT_MODE/ERASE commands are unproven - exactly what we must probe.
  - Answering it = tools/run_boot0_marker_test.py: load RAM-loader, write a
    CLSCMRKR probe to boot0 sector 2048 (dead slack, non-executed, boot0's
    SBL2/SBL1 + GPT CRCs untouched), read it back. Device stays bootable.

[2] BUILT
  - tools/bblink.py           raw USB link (probe/info/cmd2/cread/dump/
                              preflash/f7/rawseq/selftest)
  - tools/run_boot0_marker_test.py   the gate test (write/check/full)
  - loader: /tmp/opencode/bb10mt/loaders/loader_9700270A-00.bin (Classic
    SQC100-4, signed MBN, load addr 0x80200000, magic @4=D7D32D1F,
    footer @-8=D7C82D1F). Passport: loader_8D002C0A-00.bin, addr 0x0DD00000.
  - repacked image: priv-research/classic-emmc/boot0_repacked.img (4 MiB,
    marker @ sector 2048 confirmed: b'CLSCMRKR\x01..\x08')

[3] HOW TO RUN (user hands-on)
  1. Power the Classic totally off (device currently boots 10.3.3.3216 rooted).
  2. Plug USB into the Linux box -> enters BootROM (device appears as PID 0001;
     verify: python3 tools/bblink.py probe)
  3. python3 tools/run_boot0_marker_test.py write
     -> bring-up + preflash(0x15) + F7 probe block write to boot0
  4. python3 tools/run_boot0_marker_test.py check  -> CREAD read-back, look for
     the marker.
  5. Reboot phone (replug / bblink reboot). Marker is in unexecuted slack, so
     the OS should still boot => test is non-destructive.
  OUTCOMES:
    PASS  -> boot0 is writable via EDL on the original chip. Proceed to
             Passport: dump boot0+user (loader raw read), run imggen, raw-write
             new_boot0/new_user via the same lane. No desolder needed.
    REFUSE -> F7/ERASE to boot0 rejected by loader. No-desolder Android is off
             the table on the original chip (would need a fresh chip + desolder
             + ext_csd[179]=0x08). Classic stays bootable.

[4] NOTE ON THE F7 WRITE MODEL
  The marker probe writes a SINGLE B16K block via $F7 with the raw block#
  constructed from the byte offset. We deliberately do NOT call Complete/40C0
  on the probe (that finalizes a commit); the write+readback alone answers the
  addressability question. If F7 needs a different offset/geometry we will see
  the marker land elsewhere and iterate via bblink dump/cread. bblink 'cmd2'
  and 'rawseq' give brute-force access to $DE/$E5/$EE/$F7 for that iteration.

[5] ALSO NOTED
  - bb10mt's dummy 560-byte install-seal (uconsts.pas GenDummySig) layout: FF
    padding with ECC_512@$b0($bc/$10001/$B5A60BFD), ECC_256@$16c($88)/$10001/
    $C6B71C0E, RSA@$220($b4/$10001/$D7C82D1F). Matches cap.exe 560 block
    findings (session12). bb10mt sends file-embedded or dummy sig after every
    flash - this is the "install seal" over F9 40.
  - PreFlash $15 (Classic family 0x27) vs $40 (Passport family 0x2c):
    bb10mt picks by (modelID & 0xffff)==0x2c0a.

ARTIFACTS
  tools/bblink.py                 protocol port + CLI
  tools/run_boot0_marker_test.py  gate-test driver
  priv-research/bb10mt-src/       upstream source (github.com/bb10root/bb10mt)
  priv-research/classic-emmc/     boot0(img/repacked), loader copies
===============================================================================