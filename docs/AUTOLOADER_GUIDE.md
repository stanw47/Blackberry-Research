# Passport Android autoloader — build, flash order, and the boot0 step

Status: **2026-09-08**. `Passport_Android_balika_v2.exe` flashes fully (OS +
radio + Android user GPT) but the device shows **bb10-0015** because boot0 is
still the stock BB10 SBL. The finishing step — flashing Android SBL
(`boot0.img`, a.k.a. **"boot0"**) — is now a separate, probe-first tool:
`tools/boot0_flash.py`. This document explains how to make an autoloader from
scratch, what it flashes, and how to run the boot0 step.

All tooling lives in `/home/stanw47/Documents/blackberry-research/tools/` and is
plain CPython 3 (no third-party libs) **except** the live-USB tools
(`bblink.py`, `boot0_flash.py`), which need `pyusb` + `libusb` on the machine
physically attached to the device.

---

## 1. What an autoloader actually is

A RIM BlackBerry 10 autoloader `.exe` is a **self-extracting official updater**,
not a flash blob. Structure (byte-verified on both the pre-rooted Passport
exe and our rebuild):

```
[ cap.exe stub                       ]   cap_end = end of PE last section (0x8D2E00)
[ ver2 header                        ]   12 B sig = 0x97C5D59C x3, then 80 zero
                                          bytes, u32 LE file-count @ +0x5C, 4 zero
                                          bytes, then N x 8-byte absolute file
                                          offsets @ +0x64, zero-padded to cap_end+0x84
[ payload file #0 : <name>.signed    ]   a QCFM "multi-header file" (mfcq), one
[ payload file #1 : <name>.signed    ]   per logical stream group (see below)
...
```

`cap.exe` (9.2 MB, RIM CFP updater core) reads the ver2 table at run time,
opens each `.signed` payload, sniffs its type, and drives the device's loader
through the flash protocol. Everything after `cap_end` is our responsibility;
the whole structure is **reproducible byte-for-byte**.

### Anatomy of a `.signed` (QCFM multi-header file)

Containers are `mfcq`-magic files (format decoded from `bb10mt-src/qcfm.pas`
and verified byte-exact against the official `v2.0.signed`):

```
offset 0x00  V1 header  'mfcq' , checksum=0, version=1, nheaders=0,
                      headersz=0x188, datachecksum=0, flags=0x20
offset 0x20  V2 header  'mfcq' , version=0x20000, length=0x1C, nfiles=N,
                      headersz=0x168 + N*0x3C
     0x3C    1 control record pair per stream:
              PFCQ (0x2C)  magic 'pfcq' v0x20000 len=0x3C type rrecOff=0x2C
                           nrec=1 hwv=0 bs=0x10000
              RRCQ (0x10)  magic 'rrcq' len=0x10 offset=0 Count=#blocks
     0x188   data: each stream zero-padded up to 65536-byte (0x10000) blocks
```

**Image types** (qcfm.pas `Ext2Type` / observed in the Passport pair):

| ext | type | note |
|-----|------|------|
| `.ufs`    | 0x05 | user area image |
| `.mbr`    | 0x06 | OS master boot record |
| `.sig`    | 0x07 | legacy signature |
| `.ifs`    | 0x08 | QNX IFS (kernel+apps) |
| `.rcfs`   | 0x09 | QNX root (core OS) |
| `.os`     | 0x18 | OS image |
| `.sig2`   | 0x89 | signature v2 (64 KB) |
| `radio.rcfs` 0x0C / `radio.sig2` 0x8C / `radio.mbr` 0x0A | v2.1 radio streams |

The BB10 **radio** container (`v2.1.signed`) has its own header geometry
(headersz 0xF0/0x110) and keeps ~560 extra tail bytes vs the pure formula — it
is shipped through untouched (`cap.exe` tolerates it).

### Signature trailer (and why we omit it)

Official `v2.0.signed` ends with `FF FF FF FF 41 10 E1 E5` (8 bytes). The CRC
algorithm could **not** be recovered (exhaustive std/MPEG2/CRC32C and block
XOR/SUM combos all failed to match). `cap.exe` only transmits a trailer when
its length is non-zero, and community autoloaders built by bb10mt pack without
it and flash fine — so our packs omit it. Repacking the official container
with our `qcfm_pack.py` is **header-identical and data-identical**, size = −8
(the intended delta).

---

## 2. Making an autoloader (end to end)

### 2.1 Extract the streams from an existing exe

The pre-rooted Passport exe splits into:

```
Passport_10.3.03.3216_SQW100-1-2-3-4-root_v2.0.signed (3,012,034,960 B):
  IFS 10,485,760 B (160 blk) | rcfs 402,849,792 B (6147 blk)
  sig2 65536 B (1 blk) | mbr 65536 B (1 blk) | ufs 2,598,567,936 B
Passport_10.3.03.3216_SQW100-1-2-3-4-root_v2.1.signed (38,470,464 B): radio
cap.exe (9,252,352 B)
```

Extract them: locate `cap_end` via the PE headers, read the ver2 table, slice
each `.signed` by its (offset,size) span. (The split files are already parked
in `priv-research/autoloaders/passport-rooted/`.)

### 2.2 (Android variant) swap the user image

For Balika/Android, only the OS container's user stream changes:

```bash
# 1) pack the OS container with the Android GPT image instead of the stock ufs
python3 tools/qcfm_pack.py v2.0-android.signed \
    Passport_10.3.._v2.0.0.ifs \
    Passport_10.3.._v2.0.1.rcfs \
    Passport_10.3.._v2.0.2.sig2 \
    Passport_10.3.._v2.0.3.mbr \
    working/new_user.img,5        # "type 5" override - stream named .ufs role

# 2) assemble the exe: cap.exe + Android OS container + stock radio container
python3 tools/make_autoloader.py --cap shroot/cap.exe \
    --out autoloaders/passport-android/Passport_Android_balika_v2.exe \
    v2.0-android.signed v2.1.signed

# 3) validate the result
python3 tools/check_autoloader.py autoloaders/passport-android/Passport_Android_balika_v2.exe
```

`v2.0-android.signed` (824,508,808 B) contains `IFS + rcfs + sig2 + mbr +
user(new_user.img, 6272 blk)`. The built exe is 872,231,756 B, SHA256
`66f4e587923e6f00e4397c8bca5a51c3df17db6dd88f35aef415e41a5074ac2b`, and the
embedded user stream at `0x1932300C` SHA256-matches `new_user.img` exactly.

### 2.3 Checksums / validation

- `check_autoloader.py` parses every embedded container (v1/v2 `mfcq`,
  PFCQ/RRCQ records, block counts, expected container bytes) and verifies
  `OS container bytes == header+streams` exactly (+0 OK) with radio as
  passthrough (+560 tail, expected).
- A from-scratch rebuild of the official exe must be **byte-identical**
  (`sha256sum` equal) — this is the no-Wine stand-in for `cap.exe FILEINFO`.

---

## 3. Why boot0 can't ride the container (the whole reason for the tool)

boot0 is the **hardware Boot0 MMC partition** (MCT kind `$2B`, "Boot0 MMC",
4 MiB) that holds SBL1/SBL2 + the GPT boot image. The `.signed` streams route
only to OS/user/radio regions — there is **no container type for boot0**
(qcfm.pas `Ext2Type` has no boot0 entry). A boot0 write must go through the
loader's raw flash lane, which is exactly what the device's `0x2019` NVRAM
unlock (bits 42/43 = byte5 `0x0C`, already set and persisted) gates.

So the Android conversion is two steps:

1. **boot0 step** — `boot0_flash.py` writes `boot0.img` (Android SBL,
   validated: GPT @ LBA1, hwi `product = "wolverine"`, D1DC4B84 stage1/2,
   stage3 ELF, bbss, sbl1r, tz/rpm/sdi, abootr; fits in 4 MiB).
2. **user step** — the Android autoloader writes the Android GPT
   (`new_user.img`: nvram+cal_work+cal_backup+aboot+sbl1+blog/prdid+modem,
   system/vendor/data all inside the user region). BB10 never boots once
   Android SBL is active.

---

## 4. The boot0 flash step (`tools/boot0_flash.py`)

### Device-state rules (learned the hard way)

- BootROM entry requires the device to boot to the **stock OS**. A wiped
  device sits in its resident **"Reload OS" loader** (PID 0x8001) which speaks
  only the *official-updater* protocol and ignores `bblink` — recover BB10
  with the pre-rooted autoloader first.
- The device only enumerates as BootROM when a host tool is **already
  listening**. Ritual: start the tool on the attach PC → power the phone OFF →
  plug it in.
- An aborted/unknown-state BootROM password exchange triggers a **full
  security wipe**. Never start a handshake unless the device is confirmed in
  BootROM with stock OS.

### Usage (run on the USB-attached machine — Linux or Windows)

```bash
pip install pyusb libusb-package

# 0) offline sanity (no device needed)
python tools/boot0_flash.py selftest
python tools/boot0_flash.py verify-image working/boot0.img

# 1) READ-ONLY preflight: handshake + print FlashRegions + MCT
#    (Boot0 kind $2B range/flags), NO writes.
python tools/boot0_flash.py preflight

# 2) NON-COMMITTING marker probe: writes 'CLSCMRKR' into boot0 dead slack
#    (sector 2048, never executed, boot chain untouched), reads it back.
#    No Complete/signature is sent. Device stays fully bootable.
python tools/boot0_flash.py probe

# 3) FULL write (only after the probe lands): ERASE-free block stream of
#    boot0.img, 560-B install seal, Complete, verify read-back, reboot.
python tools/boot0_flash.py write --image working/boot0.img
```

The tool exits before any destructive step unless the probe verifies boot0
addressability, and prompts `COMMIT` for the full write. The verify read-back
compares boot0 against `boot0.img` before rebooting into Android SBL.
Loader: `tools/loaders/loader_8D002C0A-00.bin` (Passport, load addr
`0x0DD00000`, magic @4 `D7D32D1F`, footer @-8 `D7C82D1F`). Preflash family =
`0x40` (Passport / model 0x2C0A).

### Risk register (honest)

| risk | severity | mitig |
|------|----------|-------|
| wipe on failed BootROM handshake | high | listener-first, verified BootROM, gloves-on code, don't poke re-pulls |
| boot0 raw-lane addressability unproven | high | marker probe (non-committing) gates the full write |
| loader partition-select plumbing unknown | medium | probe read-back; iterate with `bblink rawseq` before `--force` |
| locked device / wrong loader | medium | match loader to model; never mix dev-build vs prod images |

Prudent path before touching the Passport: run the same marker probe on the
**spare Classic** (`boot0_flash.py probe --loader loaders/loader_9700270A-00.bin`
+ `--preflash 0x15` support can be added) to gain confidence in the lane.

### Conservative flash ordering for a bb10-0015 device

```
1. Flash Passport_10.3.03.3216_SQW100-1-2-3-4-root_v2.exe (stock pre-rooted
   autoloader) -> BB10 boots again, 0x2019 unlock survives (NVRAM untouched).
2. Run boot0_flash.py (preflight -> probe -> write boot0.img)
   -> device now boots Android SBL.
3. Flash Passport_Android_balika_v2.exe (Android OS+radio+user GPT)
   -> Android user area lands; next boot = Android.
```

If the device is already on Android user content, step 3 can be skipped — boot0
alone completes the conversion.

---

## 5. Recovery and the bb10-0015 error

- **bb10-0015** = "corrupt filesystem" boot-time error. It appears because
  boot0 is still the BB10 SBL: BB10 boots, finds the user partition holding the
  Android GPT, and declares the filesystem corrupt. The flash itself fully
  succeeded.
- **Recovery** = re-running any stock pre-rooted autoloader (the resident
  loader obliges the official updater). Verified repeatedly on this unit.
- After the boot0 step, boot0 is Android SBL, so BB10 is never entered and
  bb10-0015 cannot recur; `Passport_Android_balika_v2.exe` becomes the
  *forward* path, and the pre-rooted autoloader remains the fallback to restore
  BB10 if you ever re-flash a stock boot0.

---

## 6. The official-updater SBL1 lane (research status)

`cap.exe` contains the full RIM boot-image machinery: `BootromFileImage` /
`BootchainFileImage` classes, `MCT_BOOT0_MMC` / `MCT_BOOT1_MMC` region handling,
"Switch Boot Partition..." (`SWITCH_BOOT`), and a "bootrom binary" file
classification. That is the *official* SBL1-update path the `0x2019` unlock
gate is meant to enable — potentially a no-wipe, autoloader-carrying boot0
route. The bootrom file header format is still buried in virtualized C++ and
needs a focused Ghidra pass (`FUN_00432460` -> `BootromFileImage::LabelFileImage`
chain) + on-device confirmation; `boot0_flash.py` is the working no-desolder
vehicle today.

---

## 7. Artifact inventory

| artifact | path | size |
|----------|------|------|
| Android autoloader | `autoloaders/passport-android/Passport_Android_balika_v2.exe` | 872,231,756 B |
| Android OS container | `autoloaders/passport-android/v2.0-android.signed` | 824,508,808 B |
| Android SBL ("boot0") | `working/boot0.img` | 3,896,320 B (SHA256 `28a82c86205c9e0fc85df7c6fab9991334e1606f864877209e0e9280d18ec8c6`) |
| Android user GPT | `working/new_user.img` | 411,041,792 B |
| stock pre-rooted exe (recovery) | `autoloaders/passport-rooted/` | split payloads + cap.exe |
| Passport RAM-loader | `tools/loaders/loader_8D002C0A-00.bin` | 222,624 B |

Tools: `qcfm_pack.py` (container pack) · `make_autoloader.py` (exe assembly) ·
`check_autoloader.py` (validation) · `boot0_flash.py` (boot0 step) · `bblink.py`
(raw USB link). The only write-capable step is `boot0_flash.py write`; every
autoloader can be rebuilt and validated offline, byte-for-byte.