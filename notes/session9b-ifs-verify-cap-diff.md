================================================================================
SESSION 9B - IFS VERIFICATION TEST + ROOTED CAP.EXE DIFF + PUBLIC TOOL HAUL
================================================================================
2026-09-04, Classic (MSM8960, 10.3.3.498). Follows 9a (live ext_csd re-read).
Pure Windows toolchain (python 3.x + our own ports; bb10mt.exe itself unusable).

--------------------------------------------------------------------------------
[1] FLASH-SET GEOMETRY FINALLY COMPLETE (Classic OS.signed unpacking)
--------------------------------------------------------------------------------
Using qcfm.py (faithful port of bb10mt's qcfm.pas; requires working struct sizes
S_MHF1 <4sIIIIII4s=32, S_MHF2 <4sIIIIII=28, S_CF1 <4sIIIIIIII4s=40,
S_CF2 <4sIIIIIIIIII=44, S_RR2 <4sIII=16) the full partition layout is:

  OS.signed    -> part0.rcfs (398 MB, magic rimh)    | part1.sig2 (64K)
                   part2.mbr  (64K, magic eb109000)  | part3.ufs (1.8 GB)  [pfcq 0x09/0x89/0x06/0x05]
  Radio.signed -> radio.rcfs (54 MB, rimh) + radio.sig2 + radio.mbr (eb109000)
  Extra.signed -> part0.IFS  (10,944,512 B, magic FE 03 00 EA)  [pfcq type 0x08]

KEY: the IFS is NOT in OS.signed (earlier magics scan of OS.signed found only
scattered FE0300EA). It lives in Extra.signed. This closes the 7-series open
question about "where is the boot image on the Classic".

--------------------------------------------------------------------------------
[2] PACK ROUND-TRIP VALIDATED (qcfm.py pack_mfcq)
--------------------------------------------------------------------------------
* Unpack Extra.signed -> part0.ifs; re-pack (ver=2 fast, single run rr=(0,167))
  -> repacked payload is BYTE-IDENTICAL (10944512 B).
* Header difference: bb10mt pack produces 120 B header (MHF2.headersz=0, no sig
  gap); original uses 152 B header (MHF2.headersz=0x78 + 32 reserved zeros).
  Repack can be padded to identical length for in-place splicing.
* Fixed bug while testing: S_MHF1.pack_into needs all 8 fields; flags/headersz
  were struct.pack_into('<I') so offsets would write -- now correct.

--------------------------------------------------------------------------------
[3] AUTOLOADER SPLICE TOOL (make_autoloader.py) - REBUILD WITHOUT DBBT
--------------------------------------------------------------------------------
Parses the original .exe (cap.exe + separator/password/dataHeader + 3 .signed
with recorded qint64 offsets), then swaps a SAME-LENGTH .signed in place.
Needed because bb10mt.exe binary exits-1 with empty output on Windows even with
staged liblzo2.dll; DBBT not used -- the -patched.exe itself is the carrier.
Two artifacts built from SQC100-1.Classic.BB10_3_3.10.3.3.498-patched.exe:
  _baseline_pipeline.exe  (Extra repacked w/ own 120B header, payload untouched)
  _ifs_test_1byte.exe     (1 byte flipped in IFS payload @0x100098, header intact)

--------------------------------------------------------------------------------
[4] EXPERIMENT: MODIFY A CORE FILE, DOES IT BOOT?  -- RESULT: NO (RED BLINK)
--------------------------------------------------------------------------------
* Flashed _ifs_test_1byte.exe on the powered-off Classic (run exe first, then
  plug in -- "Connecting to Bootrom" prompt). 
* LED behaviour: blinking RED -- device refuses the modified IFS.
* CONCLUSION: bootloader DOES verify IFS-image integrity. Matches root.sx
  statement "integrity of the ifs-image is verified by the bootloader".
  THIS EXPERIMENTALLY CLOSES the 7>>9 series question on IFS.
* Recovery: reflashed the ROOTED (-patched) image; device back to normal.
  Blinking is fully recoverable by re-flash (confirms: product brick-tolerant).

--------------------------------------------------------------------------------
[5] THE ROOTED AUTOLOADER'S cap.exe: 3-BYTE DIFF vs STOCK (binary diff)
--------------------------------------------------------------------------------
Diff'ed SQC100-1.Classic...498.exe (stock, 2283354204 B) vs ...-patched.exe
(rooted, 2283353560 B; patched cap.exe attributed to FerreiraPablo's
BlackberrySystemPacker/Clean-R2 lineage per public posts). DataHeader/offsets
differ (Sachesi rebuild) but the cap.exe stub differs in EXACTLY 3 bytes:

  0x0000c913  84 C0 (test al,al; je +0x53)   ->  38 C0 (cmp al,al; je ALWAYS)
              => validation-call return value IGNORED; the post-validation
                 dispatch block (0xc917..0xc967, non-'1'/'3' code paths) is
                 skipped unconditionally. This is the "allow unsigned QCFM"
                 change -- loader treats every signature check as PASSED.
  0x00044959  b8 6C 00 00 00 (mov eax,0x6c)  ->  b8 00 00 00 00 (error=0)
  0x00044977  b8 49 00 00 00 (mov eax,0x49)  ->  b8 00 00 00 00 (error=0)
              two devctl-command error returns neutralized to SUCCESS.
              (Serial dispatcher: 8a 44 24 04 / case 0x0f / case 0x2e / etc.)

Everything else in cap.exe identical => the "root patch" is a minimal 3-byte
signature-validation bypass, no backdoor. (Per reddit: verification was known
to be "software layer", balika reported fl:ashing radio cleared it, Ferreira
bypassed via CAP modification -- consistent with what we see.)

--------------------------------------------------------------------------------
[6] PUBLIC TOOL HAUL FROM bb10.root.sx (his own site, all free)
--------------------------------------------------------------------------------
Downloaded D:\...\Downloads: bb10mt x4 (alpha v0.5.9.999, v0.5.0.5, v0.2.1.3,
v0.1.0.10), mod_nvram (downgrade tool + src), asroot (src), ramloader.txt
(command list), rsa_forge.py (RSA PKCS1 v1.5 e=3 forge PoC),
unlock_path_trust.zip (+ unlock_path_trust.c source - pathtrust 0x73 MsgSend to
0x40000000 proc, flags/pid/dev/ino -> 8960 10.3.3.3216).

NOTE (important): the RAW-eMMC items are PRIVATE, never published publicly:
  12 emmc firmware        /private/MAG2GA_fw.zip
  13 emmc driver patcher + fw reader  /private/sdmmc.zip
The patched SDMMC driver (custom handler exposing CMD0..CMD255 via a
DCMD_SDMMC_ANY devctl sdmmc_raw_cmd struct, incl. FUNC_CLEAR_WP) is therefore
not redistributable; we must REIMPLEMENT raw-MMC ourselves (see 8c levers +
user-space SDHCI/IOPRIV plan).

--------------------------------------------------------------------------------
[7] WHERE THIS LEAVES US
--------------------------------------------------------------------------------
* Proven: IFS verified (9b); UFS/user partition freely modifiable & boots
  (michioxd, BbSysPacker "Clean R2", root.sx pre-rooted "autoroot" images);
  RCFS editable (root.sx impersonation research) but rfs_validator in IFS
  checks os; Radio separately checked.
* The IFS wall is IMMOVABLE in software => to boot self-made boot
  images/LineageOS the ONLY known route is replacing boot0 (which the PBL
  does NOT itself verify on these 8960s) => needs a way to WRITE boot0.
  Boot0 writes need B_PWR_WP_EN cleared (9a: BOOT_CONFIG_PROT=0, temporary,
  clearable by CMD6 173=0). We are missing only a RAW MMC command channel.
* Candidate paths: 9b/8c driver .data thunk/FP redirect; user-space SDHCI
  controller access via mmap_device_io + ThreadCtl IOPRIV on ROOTED device;
  RAMLoader-side (ramloader.txt has DD FLASH_DUMP / EE ERASE_SECTOR / B7 hash
  etc.); pre-rooted Q20 10.3.3.3216 device as ready-made root carrier.
================================================================================