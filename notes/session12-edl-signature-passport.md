# Session 12 — EDL latched; OS flash red-blink root-caused to cap.exe stub signature; Passport no-desolder conversion feasibility 2026-09-07

## Status: Classic RECOVERED & BOOTING

- Windows `cap.exe`-style autoloader (`Z30_10.3.03.3216_STA100-1-2-3-4-5-6-root_v2.exe`)
  flashed to the Classic boots it **successfully**.
- This is the decisive control experiment: bb10mt flashing the **byte-identical**
  OS+radio carriers produced red-blink; the Windows stub boots them. The payload
  is NOT the problem — the stub's flash-time behavior is.

## EDL RAM-Loader pipeline now fully working (Linux)

- Loader source: `loader_9400270A-00.bin` (245,468 B) placed as
  `loaders/loader_9700270A-00.bin`. `bb10mt.ini` has NO `9700270a` entry, so we
  register the Classic (LDR_00-family) loader under the `9700270A` name.
- Runner (`bb_flash_run.py`) auto-feeds the device password on every prompt
  (twice per invocation — pre-loader and post-loader-init).
- Full `info` read obtained: hwid `0x9700270a`, BootROM 5.46.0.11, PIN 2C22528E,
  BSN 1160442668, MMC partition map (boot0 0-31, user 32-262143, ...), OS
  `10.3.3.3216 DEV` builder "developer" Feb 21 2018.
- Flash of the 3 GB OS carrier completes 100%, "Done", reboot issued — yet the
  device red-blinked on every bb10mt flash. That contradiction is resolved below.

## Red-blink root cause: the OS install seal (cap.exe signature block)

### The 560-byte trailer contract
- RAM-loader command `F9 40 = SIGNATURE_TRAILER` is the 560-byte seal that SBL
  checks to consider the OS install valid.
- bb10mt strips the last 560 bytes of a carrier ONLY if bytes at `len-560`
  begin with `QNXH` (0x48584e51), then sends them over F9 and does NOT stream
  them as data.
- `classic_root.0.signed` ends with 560 **zero** bytes (no QNXH magic). So
  bb10mt (a) streamed the zeros as data and (b) sent a zero/empty F9 seal.
  The radio carrier (`classic_root.1`) DOES have a proper `QNXH-OS-1` trailer.

### cap.exe signature block extracted
- `cap.exe` embeds a PEM `-----BEGIN SIGNATURE BLOCK-----` at offset `0xebb58`.
  Fixing the base64 decode (the blob contains a `Version:` header line) yields
  exactly **560 bytes**:
  - Mostly **0xFF (EMSA-PKCS#1 v1.5 padding)**, with `010001` (e=65537) RSA
    records at offsets and the `1F2DC8D7` footer.
  - This is the block cap.exe sends over F9 40 for the OS — the genuine
    install seal.
- We rebuilt `os_capseal.signed` (carrier tail 560 zeros replaced by cap's real
  block; identical total size) and flashed it via bb10mt. 100% done, clean
  `Send signature` + reboot, **but still red-blink**. Conclusion: merely sending
  the correct 560 over F9 is insufficient — SBL's OS check involves more of the
  flash-time state that cap.exe sets up (secure-boot chain state with the loader,
  or an additional in-band signature the stream must carry).
- This is why the Windows stub is indispensable: the flash tool has to replay a
  handshake/injection that bb10mt does not reproduce.

### Key remaining unknown (now the #1 technical gate)
- Exactly what cap.exe's stub does at flash time that bb10mt doesn't:
  (a) an extra loader command (signature/hash exchange) beyond F9,
  (b) PreFlash byte = 0x15 handling,
  (c) an in-stream signature region rewritten before streaming.
- Since the SAME carriers boot under Windows, a packet-level capture of cap.exe
  vs bb10mt on identical inputs would pin it. This is the lowest-risk, highest-
  value next experiment now that the device is back.

## imggen port for Classic — SoC reality check

- User supplied `imggen` source + prebuilt binaries plus the Passport conversion
  guide (balika011.hu). imggen = MSM8974 Passport conversion (boot0+user GPT +
  SBL tz rpm aboot NON-HLOS images).
- Verified the Classic (SQC100) is **MSM8960/AB** (PM8921/PM8922 PMIC strings in
  the boot0 dump; Adreno 225, Snapdragon S4).
- Classic boot0 real dump (`boot0.img`, 4 MiB) parsed:
  - GPT partitions: **SBL2** (LBA 34-521, 249,856 B) then **SBL1** (LBA 522-719,
    101,376 B). This is the MSM8960 SBL2-first boot chain.
  - Build info (11.0.46.5, ec_agent, Jul 8 2014, hwid 0x9700270a, secure=true).
- imggen only supports hwids `0x8d/8e/8f002c0a` (oslo) + `0x84-0x8c002c0a`
  (wolverine/Passport) — all **MSM8974 family byte 0x2c**. Classic family byte
  is **0x27** (`0x9700270a`). imggen hard-refuses the Classic hwid, and more
  importantly its bundled loaders are MSM8974 code that an MSM8960 bootROM
  cannot run. **No public MSM8960 Android conversion exists.**
- Conclusion: imggen port for the Classic is NOT a path to Android — the SoC
  mismatch is fundamental. BUT the MCT/build_info parse logic is device-generic
  and reusable, and the Passport (MSM8974) is a perfect match.

## Classic entire boot is QCFM-hostile to boot0 writes — but a route exists

- Autoloader contains only 2 carriers (OS + radio); the stub never emits a boot0
  region. The Classic boot loader (SBL2/SBL1) lives in the **hardware boot0
  partition**, which (a) the driver write-protects, (b) no OS carrier touches.
- Verified the Classic boot0 GPT is standard EFI (valid CRCs, `EFI PART`):
  `boot0.img` parses perfectly with our gpt.py port.

## New tool: `tools/classic_repack.py` (marker test)

- Ports imggen's GPT/MCT/BuildInfo parsing to the Classic and produces a
  validated `boot0_repacked.img` with a benign `CLSCMRKR` marker written into
  physical-slack sectors (2048-2049), SBL2/SBL1 untouched, GPT CRCs recomputed.
- Purpose: prove the EDL lane can rewrite the hardware boot0 partition verbatim
  when a raw-write tool is available. This is the prerequisite for boot0
  ownership / Android conversion without desoldering.
- Verified output: 4 MiB, markers present, GPT CRCs remain valid.

## Passport no-desolder conversion — feasibility (NEW)

- The Passport = MSM8974 = imggen's only supported SoC. Confirmed assets:
  - Rooted Passport autoloader (`Passport_10.3.03.3216_SQW100-1-2-3-4-root_v2.exe`
    splits to OS 3,012,034,960 + radio 38,470,464).
  - Passport EDL loader `loader_8D002C0A-00.bin` (LDR_75 for hwid `8d002c0a`).
- The guide's desolder is only needed to (1) back up boot0+user and (2) write
  imggen output + set ext_csd 179 (BOOT_BUS_CONDITIONS). We already dump boot0+
  user from a booted rooted OS (Classic dumps prove it). The EDL lane already
  writes user partitions; the missing primitive is a raw boot0 write path.
- Remaining gaps (all provable cheaply):
  1. Raw write of a hardware boot partition via EDL (marker test above).
  2. Feed imggen raw .img outputs through a QCFM/autoloader wrap or raw-writer.
- Whether to set ext_csd 179 to 0x08 (boot0 as boot partition) — the guide's
  desolder path sets this because the chip is remounted; with the original eMMC
  the boot bus condition may already be correct. Verify on the Passport.
- Risk: EDL recovery persists after boot0 corruption (re-flash stock), and the
  imggen loaders are the correct MSM8974 parts, so worst case = EDL restore.

## Next moves
1. Capture cap.exe vs bb10mt USB traffic on identical carriers → pin the stub's
   flash-time signature/handshake delta. (Highest value; device is booting.)
2. Marker-test the boot0-write lane on the Classic using `classic_repack.py`.
3. Passport: capture boot0+user from rooted OS, verify ext_csd 179, run imggen.
4. Build the raw EDL sector-writer (F7/F8, EE, DD) to drive imggen outputs.