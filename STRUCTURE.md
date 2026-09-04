# BlackBerry BB10 Hardware Security Reference

> **Classic (MSM8960) & Passport (MSM8974AA)**

A comprehensive dissection of the BlackBerry 10 platform — hardware architecture,
boot chain, autoloader format, filesystem hierarchy, security mechanisms, unlock
methods, and research methodology. Built from reverse engineering, live device
testing, and public GPL sources.

> **DISCLAIMER**
>
> This document exists **purely as a research aid**. Nothing here is a flashing
> guide or endorsed procedure. Modifying eMMC boot partitions can permanently
> brick a device with no recovery path short of JTAG/ISP rework. Use at your
> own risk. Some artifacts reference third-party proprietary firmware (BlackBerry,
> Qualcomm). See [LEGAL.md](LEGAL.md).

---

## Table of Contents

- **[Part I: Hardware Architecture](#part-i-hardware-architecture)**
  - [1. SoC Overview](#1-soc-overview)
  - [2. eMMC Layout](#2-emmc-layout)
  - [3. Boot Partition Write-Protection](#3-boot-partition-write-protection)
- **[Part II: Boot Chain](#part-ii-boot-chain)**
  - [4. PBL — Primary Boot Loader](#4-pbl--primary-boot-loader)
  - [5. SBL1 — Secondary Boot Loader](#5-sbl1--secondary-boot-loader)
  - [6. BB10 Boot Stages](#6-bb10-boot-stages)
  - [7. IFS — Initial File System](#7-ifs--initial-file-system)
  - [8. Kernel & Device Managers](#8-kernel--device-managers)
- **[Part III: Autoloader Format](#part-iii-autoloader-format)**
  - [9. Autoloader Anatomy](#9-autoloader-anatomy)
  - [10. Image Components](#10-image-components)
  - [11. Classic vs Passport Differences](#11-classic-vs-passport-differences)
  - [12. imggen Toolchain](#12-imggen-toolchain)
- **[Part IV: Filesystem Hierarchy](#part-iv-filesystem-hierarchy)**
  - [13. PFS — Protected File System](#13-pfs--protected-file-system)
  - [14. QNX6 — Root, Data, SD](#14-qnx6--root-data-sd)
  - [15. Device Nodes](#15-device-nodes)
  - [16. NVFS / vtnvfs — Token Storage](#16-nvfs--vtnvfs--token-storage)
- **[Part V: Security Mechanisms](#part-v-security-mechanisms)**
  - [17. Boot Chain Signing](#17-boot-chain-signing)
  - [18. dm-verity](#18-dm-verity)
  - [19. Pathtrust — Filesystem Trust LSM](#19-pathtrust--filesystem-trust-lsm)
  - [20. BIDE — Integrity Detection](#20-bide--integrity-detection)
  - [21. SELinux](#21-selinux)
  - [22. GRSEC / PaX](#22-grsec--pax)
  - [23. eMMC Hardware Write-Protection](#23-emmc-hardware-write-protection)
- **[Part VI: Root & Unlock Methods](#part-vi-root--unlock-methods)**
  - [24. getroot Payload](#24-getroot-payload)
  - [25. Group Wrappers & procmgr_ability](#25-group-wrappers--procmgr_ability)
  - [26. pathtrust Whitelist Trick](#26-pathtrust-whitelist-trick)
  - [27. boot0 Modification](#27-boot0-modification)
  - [28. Prototype Bootloader Generation](#28-prototype-bootloader-generation)
  - [29. EDL / Firehose / Sahara](#29-edl--firehose--sahara)
- **[Part VII: Research Methodology](#part-vii-research-methodology)**
  - [30. QNX MMC Devctl Interface](#30-qnx-mmc-devctl-interface)
  - [31. /proc/\<pid\>/as Memory Patching](#31-procpidas-memory-patching)
  - [32. Reverse Engineering](#32-reverse-engineering)
  - [33. Live Debugging](#33-live-debugging)
- **[Part VIII: Status & Open Questions](#part-viii-status--open-questions)**
  - [34. Current State](#34-current-state)
  - [35. B_PWR_WP_EN Clearing](#35-b_pwr_wp_en-clearing)
  - [36. /proc/as Ability Gate](#36-procas-ability-gate)
  - [37. Future Work](#37-future-work)
- **[Appendices](#appendices)**

---

# Part I: Hardware Architecture

## 1. SoC Overview

### BlackBerry Classic

| Attribute | Value |
|---|---|
| SoC | Qualcomm MSM8960 (secboot3) |
| HWID | `0x9700270a` |
| Codename | mockingbird / ontario |
| OS | BB10 / QNX |
| QNX Build | `QNX BLACKBERRY-528E` |
| Builder | `ec_agent` |
| eMMC | Toshiba 032GE4 (32 GB) |
| Modem | Qualcomm (Qualcomm PBL ROM, same as MDM9x15) |

The MSM8960 is a dual-core Krait SoC with an embedded eMMC controller (SDCC —
Snapdragon Digital Card Controller). The eMMC is exposed as `/dev/emmc/*` block
devices via the `devb-sdmmc-rim-msmsdcc` driver (BlackBerry's vendor fork of the
QNX `devb-sdmmc` block device manager).

### BlackBerry Passport

| Attribute | Value |
|---|---|
| SoC | Qualcomm MSM8974AA (Snapdragon 800) |
| HWID variants | `0x84002c0a` (SQW100-3/NA), `0x85002c0a` (SQW100-2/VZW), `0x86002c0a` (Sprint), `0x87002c0a` (SQW100-1/EMEA), `0x8c002c0a` (Wichita) |
| Codename | WINDERMERE EMEA / "wolverine" (imggen) |
| OS | BB10 / QNX |
| QNX Build | `QNX BLACKBERRY-603C` |
| Related "oslo" variants | `0x8d/8e/8f002c0a` (windermere2/3/4, SQW100-4/ROW) |

The MSM8974AA is a quad-core Krait 400 SoC. Same SDCC eMMC controller
architecture as the MSM8960, same driver (`devb-sdmmc-rim-msmsdcc`), same
filesystem layout. The key hardware difference is the `PBL debug mode` register
region (`0xFC4xxxxx`) and the `passport_stage3` exploit target on the RPM
co-processor.

### Key Hardware Addresses (MSM8974AA — from passport_stage3 RE)

| Address | Purpose |
|---|---|
| `0xFC401780` | GCC_WDOG_DEBUG (watchdog reset disable) |
| `0xFC4BE0F0` | BOOT_PARTITION_SELECT (`0x5D1` = PBL debug mode) |
| `0xFC100008` | RPM_APPS_STATUS_MAGIC (signal RPM ready) |
| `0xFC100080` | RPM code write target |
| `0xFE800000` | Stage3 trampoline entry |
| `0xFE820000` | Stage3 APPS payload |
| `0xF80022D4` | g_flash (flash device struct) |
| `0xFC106AE8` | g_state (PBL state) |

## 2. eMMC Layout

Both Classic and Passport share the same eMMC partition topology, exposed via
QNX device nodes under `/dev/emmc/`.

### Partition Map

```
┌─────────────────────────────────────────────────────────┐
│                    eMMC Device                          │
├──────────┬──────────────────────────────────────────────┤
│ boot0    │ 4 MB — SBL1, HWI, bbss.insecure             │
│          │ (Hardware write-protected: EROFS)            │
├──────────┼──────────────────────────────────────────────┤
│ boot1    │ 4 MB — Backup SBL1                           │
│          │ (Hardware write-protected: EROFS)            │
├──────────┼──────────────────────────────────────────────┤
│ rpmb0    │ —   — Replay Protected Memory Block          │
│          │ (Authenticated-only write)                   │
├──────────┼──────────────────────────────────────────────┤
│ nvram0   │ 4,128,768 B — NVRAM records, build-info,    │
│          │ partition map (BB10/QNX)                     │
├──────────┼──────────────────────────────────────────────┤
│ cal_work0│ —   — Calibration data                       │
├──────────┼──────────────────────────────────────────────┤
│ dmi0     │ 1,048,576 B — Device/board info              │
├──────────┼──────────────────────────────────────────────┤
│ os0      │ —   — OS slot (primary)                      │
├──────────┼──────────────────────────────────────────────┤
│ os1      │ —   — OS slot (backup/dual-boot)             │
├──────────┼──────────────────────────────────────────────┤
│ uda0     │ —   — User data area                         │
├──────────┼──────────────────────────────────────────────┤
│ radio0   │ —   — Modem firmware                          │
├──────────┼──────────────────────────────────────────────┤
│ sd0      │ —   — SD card                                │
└──────────┴──────────────────────────────────────────────┘
```

### Symlinks

`hd0`–`hd7` are symlinks mapping to the above partitions. All block devices
are owned `root:Disk_Drivers` (mode `660` / `brw-rw----`).

### Named Sub-Regions

`boot0` has named sub-regions: `boot0.01000000`, `boot0.02000000` (segmented
access for different sections of the 4 MB boot partition).

### NVRAM Partition Map

`nvram0` contains a BB10/QNX partition map defining:

| Partition | Purpose |
|---|---|
| `nvram` | NVRAM records |
| `cal_work` | Calibration work area |
| `cal_backup` | Calibration backup |
| `dmi_mbr/sig/fsys` | Device info MBR/signature/filesystem |
| `os_mbr/sig/fsys` | OS MBR/signature/filesystem |
| `system` | System partition |
| `radio` | Modem partition |
| `user` | User data |

The MCT (Master Configuration Table) is embedded in `boot0`'s build-info at
`mct_offset`/`mct_size` and defines offsets/sizes relative to the user area.

### GPT Structure

Standard GPT (revision 0x10000, 512-byte sectors). Boot GPT partitions in `boot0`:

| Partition | Purpose |
|---|---|
| `hwi` | HWI text config (product/variant/pcb_rev/pop_rev/bsis_type) |
| `stage1` | Stage 1 bootloader |
| `stage2` | Stage 2 bootloader |
| `stage3` | Stage 3 bootloader |
| `bbss` | BlackBerry Secure Suite |
| `sbl1r` | SBL1 (root) |
| `tzr` | TrustZone |
| `rpmr` | RPM firmware |
| `sdir` | SDI |
| `abootr` | Aboot (LK) |

User area GPT (on `uda0`):

| Partition | Purpose |
|---|---|
| `nvram` | NVRAM |
| `calwork_b` / `calback_b` | Calibration work/backup |
| `aboot` / `sbl1` / `rpm` / `tz` / `sdi` | Bootloader components |
| `blog` / `boardid` / `nvuser` / `perm` / `prdid` | BB config/identity |
| `modem` | NON-HLOS modem firmware |

## 3. Boot Partition Write-Protection

The boot partition write-protection is the central hardware gate blocking
bootloader unlock. It operates at the eMMC controller level, not the OS level.

### ext_csd Bytes (live from Classic)

| Byte | Field | Value | Meaning |
|---|---|---|---|
| `0xAA` | `BOOT_CONFIG_PROT` | `0x00` | NOT fused — temporary, clearable |
| `0xAD` | `B_BOOT_WP` | `0x04` | `B_PWR_WP_EN` set (power-on WP active) |
| `0xB3` | `BOOT_WP_STATUS` | `0x08` | WP status reflects B_PWR_WP_EN |

### Two Types of Write-Protection

1. **BOOT_WP (power-on, temporary):** `B_PWR_WP_EN` is re-applied by SBL1
   every boot. Within a single power-on session, clearing it via CMD6 SWITCH
   `ext_csd[173]=0` *should* work — but the card returns `SWITCH_ERROR`.

2. **BOOT_CONFIG_PROT (permanent, irreversible):** If this were set, boot0
   would be permanently unwritable. Currently `0x00` on both Classic and
   Passport, meaning the WP is *theoretically* clearable.

### Why Standard WRITE_PROTECT Fails

The QNX MMC driver's `DCMD_MMCSD_WRITE_PROTECT` devctl reaches the card
(`mmc_switch(0xad)`) but the **eMMC card rejects the CMD6 SWITCH** with
`SWITCH_ERROR`. The failure chain:

1. `nlba % wp_grp_size` check fails (EINVAL for most inputs; wp_grp ~3.2 GB
   >> boot0's 4 MB)
2. Even with valid nlba, the heap availability flag returns EIO for boot
   partitions before reaching CMD6
3. Even when CMD6 IS reached, the card rejects it — confirmed by slog2:
   `"sdmmc_write_protect: switch ext_csd_boot_wp"`

The raw-command passthrough (`VUC_CMD`) that could bypass the driver's
pre-checks is **not implemented** — it returns `ENOTTY`.

---

# Part II: Boot Chain

## 4. PBL — Primary Boot Loader

The PBL (Primary Boot Loader) is **immutable ROM code** burned into the SoC
at manufacture. It is the root of trust for the entire boot chain.

### Responsibilities

1. Initialize basic hardware (clock, DRAM, eMMC controller)
2. Read `boot0` partition from eMMC
3. Verify SBL1 signature (ECDSA P-256)
4. Hand off to SBL1 if verification passes

### Key Properties

- **No ASLR** — all PBL functions are at fixed addresses (e.g., `0xFC01B46C`,
  `0xFC015E48`, etc. on MSM8974AA)
- **Fused key storage** — the PBL's root-of-trust key is burned into one-time
  programmable fuses at manufacture
- **Not software-reachable** from the running OS — the `0xFC4xxxxx` register
  region (boot config/fuse area) is not mapped into the OS address space
- **PBL debug mode** can be entered via magic register writes (`BOOT_PARTITION_SELECT=0x5D1`)
  but requires physical access or the RPM co-processor exploit (passport_stage3)

### PBL Helper Functions (MSM8974AA)

| Address | Function |
|---|---|
| `0xFC01B220` | `pbl_state_init` |
| `0xFC015BA8` | `pbl_cold_boot_hw_init` |
| `0xFC015D54` | `pbl_data_init` |
| `0xFC017CE4` | `pbl_load_sbl` |
| `0xFC01805C` | `pbl_populate_share_data` |
| `0xFC016768` | `pbl_sdcc_init` |
| `0xFC01DAEC` | `pbl_flash_sdcc_parse_gpt` |
| `0xFC010984` | `memcpy` (ROM) |
| `0xFC01D0A0` | `memset` (ROM) |

## 5. SBL1 — Secondary Boot Loader

SBL1 is the signed secondary loader stored in `boot0`/`boot1`. It initializes
the rest of the hardware and loads the next stage.

### Responsibilities

1. Initialize DRAM, PMIC, and peripherals
2. Apply boot write-protection (`BOOT_WP` re-armed every boot)
3. Load and verify TrustZone (`tz.mbn`), RPM (`rpm.mbn`), SDI (`sdi.mbn`)
4. Load and verify aboot (Android bootloader / BlackBerry LK fork)

### SBL1 Header Format

```c
struct sbl_header_type {
    uint32_t codeword;          // flash type info
    uint32_t magic;             // 0x844bdcd1
    uint32_t RESERVED_0..2;
    uint32_t image_src;         // offset from flash/RAM start
    uint8_t *image_dest_ptr;    // load address + entry point
    uint32_t image_size;
    uint32_t code_size;
    uint8_t *signature_ptr;
    uint32_t signature_size;
    uint8_t *cert_chain_ptr;
    uint32_t cert_chain_size;
    uint32_t oem_root_cert_sel;
    uint32_t oem_num_root_certs;
    uint32_t RESERVED_5..9;
};
```

### Key Strings Found in SBL1

- `"backup_bootchain"`, `"primary_bc_ver"`
- `"usb: going for EDL"`, `"dload mode, skip rpm"`
- `"boot_dload.c"`, `"Debug board switch forcing backup boot chain"`
- `"Backup boot key combo active"`

**No fastboot/recovery/download/EDL/Sahara/9008 strings** — only "factory boot
mode" vs "product boot mode" (both OS-type gated).

### Embedded Source Path (Classic)

```
/mnt/data/mstuglik_l/e7_boot/boot_images/1.0.x/core/boot/secboot3/{msm8960/sbl1,common}/…
```

## 6. BB10 Boot Stages

After SBL1, BB10 uses a chain of signed stage images:

```
PBL (ROM, immutable)
  → SBL1 (boot0, signed, HW-verified)
    → RPM firmware (rpm.mbn)
    → TrustZone (tz.mbn)
    → SDI (sdi.mbn)
      → Aboot/LK (aboot.mbn / emmc_appsboot.mbn)
        → stage1.mbn → stage2.mbn → stage3.mbn
          → bbss.mbn (BlackBerry Secure Suite)
            → IFS (ramdisk) → Kernel → OS
```

### Stage Responsibilities

| Stage | Purpose |
|---|---|
| `stage1.mbn` | Early hardware init, load stage2 |
| `stage2.mbn` | Hardware setup, load stage3 |
| `stage3.mbn` | Final boot stage, mount IFS, verify OS images |
| `bbss.mbn` | BlackBerry Secure Suite — sets `bbss_insecure` flag, manages secure boot policy |
| `aboot.mbn` | Android bootloader (LK fork) — loads `boot.img` |

### Boot Mode Selection

SBL1 supports two boot modes:
- **Primary bootchain** (normal): `AAW068` (Priv) / specific BB10 version
- **Backup bootchain**: `AAC603` (Priv) — triggered by "Debug board switch"
  or "Backup boot key combo active"

### Key Boot Files

| File | Size | Notes |
|---|---|---|
| `sbl1.mbn` | — | Secondary boot loader |
| `aboot.mbn` | — | Android bootloader (LK fork) |
| `stage1.mbn` | — | Stage 1 |
| `stage2.mbn` | — | Stage 2 |
| `stage3.mbn` | — | Stage 3 |
| `bbss.mbn` | — | BlackBerry Secure Suite |
| `rpm.mbn` | — | RPM co-processor firmware |
| `tz.mbn` | — | TrustZone |
| `sdi.mbn` | — | SDI |
| `NON-HLOS.bin` | — | Modem firmware |

## 7. IFS — Initial File System

The IFS (Initial File System) is a ramdisk mounted early in boot. It contains
the essential scripts and binaries needed to mount the real root filesystem.

### Mount Points

| Device | Mount | FS | Options |
|---|---|---|---|
| — | `/` | qnx6 | ro, trusted |
| `/dev/emmc/os0t179` | `/base` | rcfs | ro |
| `/dev/emmc/radio0t179` | `/radio` | rcfs | ro |

### Key Files in IFS

- `/base/bin/` — system binaries (rcfs mount from `os0t179`)
- `/base/scripts/` — boot scripts including `ota_info_pps.sh`
- `/proc/boot/pathtrust` — pathtrust trust list (root:nto, 750)

### dm-verity Root-of-Trust

The verity root-of-trust key lives **inside** `boot.img`'s ramdisk, which is
ECDSA-gated. You cannot change the verity root without a signed `boot.img`.

## 8. Kernel & Device Managers

BB10 uses the QNX Neutrino microkernel. Instead of a monolithic kernel with
loadable modules, QNX uses **device managers** — separate userspace processes
that own specific hardware.

### Key Device Managers

| Device Manager | Binary | Purpose |
|---|---|---|
| `devb-sdmmc-rim-msmsdcc` | `/proc/boot/devb-sdmmc-rim-msmsdcc` | eMMC/SD block device (BlackBerry vendor fork) |
| `io-usb` | — | USB host/device stack |
| `io-pkt` | — | Network stack |
| `io-audio` | — | Audio subsystem |
| `io-hid` | — | HID input devices |
| `screen` | — | Display compositor |
| `navigator` | — | Navigation/gesture handler |
| `camera2` | — | Camera subsystem |
| `videoCore` | — | Video playback |
| `powerman` | — | Power management |
| `smmu_service` | — | SMMU (IOMMU) service |
| `qcore` | — | Core system services |
| `bide` | — | BIDE integrity detection daemon |
| `trustzone` | — | TrustZone bridge |
| `stp_dispatcher` | — | Secure Token Protocol dispatcher |

### procmgr_ability Model (MAP_DEVICE)

Every device manager that owns a device node holds `PROCMGR_AID_MAP_DEVICE`,
which is required for `MAP_PHYS` (physical memory mapping). Processes with
this ability and their physical map counts:

| Process | Phys Maps | Process | Phys Maps |
|---|---|---|---|
| screen | 496 | io-audio | 17 |
| io-pkt | 194 | devb-sdmmc(1) | 14 |
| qcore | 222 | devb-sdmmc(2) | 11 |
| smmu_service | 108 | devc-serm | 6 |
| powerman | 53 | io-hid | 6 |
| navigator | 45 | keypad | 6 |
| io-bb | 30 | bide | 6 |
| camera2 | 22 | stp_dispatcher | 4 |
| videoCore | 2 | trustzone | 3 |

**Key insight:** `MAP_DEVICE` is NOT unique to any single process. Code
execution in ANY process holding `MAP_DEVICE` yields the same latent
capability to map physical memory.

---

# Part III: Autoloader Format

## 9. Autoloader Anatomy

BB10 autoloaders are **self-extracting ZIP archives** (or `.exe` self-extractors
on Windows) that contain all the firmware images needed to reflash a device.

### Structure

```
autoloader.zip (or .exe)
├── flashall.sh          # Shell script that flashes all images
├── sbl1.mbn             # Secondary boot loader
├── aboot.mbn            # Android bootloader (LK fork)
├── rpm.mbn              # RPM firmware
├── tz.mbn               # TrustZone
├── sdi.mbn              # SDI
├── NON-HLOS.bin         # Modem firmware
├── boot.img             # Kernel + ramdisk
├── system.img           # /system (dm-verity)
├── oem.img              # /oem (dm-verity)
├── userdata.img         # /data
├── stage1.mbn           # BB10 stage 1
├── stage2.mbn           # BB10 stage 2
├── stage3.mbn           # BB10 stage 3
├── bbss.mbn             # BlackBerry Secure Suite
├── hwi                  # HWI text config
├── boot_gpt_secure.bin  # GPT template (secure)
├── boot_gpt_insecure.bin# GPT template (insecure)
└── user_gpt.bin         # User partition GPT
```

### Flash Process

`flashall.sh` (or the `.exe` wrapper) writes each image to its corresponding
GPT partition using `btool` or direct eMMC writes. The process:

1. Parse GPT to find partition offsets
2. Write each image to its partition
3. Verify writes
4. Reboot

## 10. Image Components

### Boot Images

| Image | Purpose | Signed? |
|---|---|---|
| `sbl1.mbn` | Secondary boot loader | Yes (ECDSA P-256) |
| `aboot.mbn` | Android bootloader | Yes |
| `rpm.mbn` | RPM co-processor firmware | Yes |
| `tz.mbn` | TrustZone | Yes |
| `sdi.mbn` | SDI | Yes |
| `stage1.mbn` | BB10 stage 1 | Yes |
| `stage2.mbn` | BB10 stage 2 | Yes |
| `stage3.mbn` | BB10 stage 3 | Yes |
| `bbss.mbn` | BlackBerry Secure Suite | Yes |

### System Images

| Image | Purpose | Integrity |
|---|---|---|
| `boot.img` | Kernel + ramdisk | ECDSA signed |
| `system.img` | /system | dm-verity protected |
| `oem.img` | /oem | dm-verity protected |
| `userdata.img` | /data | Not integrity-protected |

## 11. Classic vs Passport Differences

### Hardware Differences

| Attribute | Classic | Passport |
|---|---|---|
| SoC | MSM8960 (dual-core) | MSM8974AA (quad-core) |
| HWID | `0x9700270a` | `0x87002c0a` (EMEA) |
| QNX Build | `528E` | `603C` |
| Board | mockingbird/ontario | WINDERMERE |
| Stage3 exploit | N/A (different PBL) | `passport_stage3` (RPM→PBL) |

### Boot Chain Differences

Both share the same BB10/QNX boot chain architecture, but:
- The **PBL register regions** differ (MSM8960 vs MSM8974AA)
- **passport_stage3** targets MSM8974AA-specific registers (`0xFC4xxxxx`)
- The MSM8960's PBL has different debug mode entry points
- SBL1 embedded source paths differ (`msm8960/sbl1` vs `msm8974/sbl1`)

### Autoloader Differences

Passport autoloaders contain MSM8974AA-specific images:
- `sbl1.mbn` compiled for MSM8974AA
- `rpm.mbn` compiled for MSM8974AA RPM co-processor
- `tz.mbn` compiled for MSM8974AA TrustZone
- Stage images target MSM8974AA memory map

## 12. imggen Toolchain

`imggen` is the **public GPL tool** that generates prototype bootloader images.
It is the key to understanding how `bbss.insecure` enables the unlock.

### What imggen Produces

1. **Prototype bootloader images** — stage1/2/3.mbn, bbss.mbn
2. **GPT templates** — `boot_gpt_secure.bin` and `boot_gpt_insecure.bin`
   (2,560 bytes each, differ at **byte 529** — GPT partition table CRC)
3. **HWI partition** — text config with product/variant/pcb_rev/pop_rev +
   FNV1a checksum

### bbss.insecure Flag

The flag is stored in `boot0`'s `build_info` structure:

| Location | Value | Meaning |
|---|---|---|
| `boot0` offset `0x35a98` | `0x00000000` | SECURE (stock) |
| `nvram0` offset `0x18098` | `0x00000001` | INSECURE (getroot artifact) |

**`_BUILD_INFO_FORMAT`**: `"<II4sI64s16s16s12sII...x22...40s1024s>"`

Field 8 (u32 @ offset `0x7c` within build-info) = SECURE flag:
- `0` = secure (SBL1 signature verification enforced)
- non-zero = insecure ("insecure device; ignoring SBL auth failure!")

When set to non-zero, `bbss.mbn` skips SBL1 signature verification, allowing
the prototype bootloader (generated by imggen) to load without valid signatures.

### Boot GPT Templates

| File | Size | Notes |
|---|---|---|
| `boot_gpt_secure.bin` | 2,560 B | Secure GPT template |
| `boot_gpt_insecure.bin` | 2,560 B | Insecure GPT template; differs at byte 529 |

---

# Part IV: Filesystem Hierarchy

## 13. PFS — Protected File System

BB10 uses QNX's **rcfs** (ROM Compact File System) for read-only system
partitions. These are raw eMMC partitions mounted as rcfs:

| Device | Mount | FS | Contents |
|---|---|---|---|
| `/dev/emmc/os0t179` | `/base` | rcfs | OS boot scripts, system binaries |
| `/dev/emmc/radio0t179` | `/radio` | rcfs | Modem firmware |

### /base Structure

```
/base/
├── bin/            # System binaries (rcfs, ro)
├── scripts/        # Boot scripts (rcfs, ro)
│   └── ota_info_pps.sh  # Autoroot entry point
├── dev/            # Device nodes
├── etc/            # Configuration
├── lib/            # Libraries
└── proc/           # Procfs mount point
```

The `/base/bin` mount is a separate rcfs from `os0t179`, mounted on top of
`/base` (which is itself rcfs). This creates a layered read-only filesystem.

## 14. QNX6 — Root, Data, SD

The main filesystem is QNX6, mounted from `/dev/emmc/user0`:

| Device | Mount | FS | Purpose |
|---|---|---|---|
| `/dev/emmc/user0` | `/` | qnx6 | Root filesystem |
| `/dev/emmc/user0` | `/sdcard` | qnx6 | SD card mount |
| `/dev/emmc/user0` | `/data` | qnx6 | User data |
| `/dev/emmc/cal_work0` | `/efs` | qnx6 | Calibration data |
| `/dev/emmc/sd0` | `/accounts/1000/removable/sdcard` | dos/fat32 | External SD |

### Filesystem Properties

- **Root (`/`)**: `ro, trusted` — read-only, trusted by Pathtrust
- **`/data`**: `forceencrypt` — NOT trusted by Pathtrust
- **`/efs`**: calibration data, not trusted
- **`/accounts/.../sdcard`**: FAT32, not trusted

## 15. Device Nodes

All eMMC block devices are under `/dev/emmc/`, owned `root:Disk_Drivers`
(mode `660` / `brw-rw----`):

| Device | Partition | Write Status |
|---|---|---|
| `/dev/emmc/boot0` | Boot partition 0 | **EROFS** (HW write-protected) |
| `/dev/emmc/boot1` | Boot partition 1 | **EROFS** (HW write-protected) |
| `/dev/emmc/rpmb0` | RPMB | Authenticated-only |
| `/dev/emmc/nvram0` | NVRAM | Writable |
| `/dev/emmc/dmi0` | Device info | Writable |
| `/dev/emmc/os0` | OS slot 0 | Writable |
| `/dev/emmc/os1` | OS slot 1 | Writable |
| `/dev/emmc/uda0` | User data | Writable |
| `/dev/emmc/user0` | User area | Writable |
| `/dev/emmc/cal_work0` | Calibration | Writable |
| `/dev/emmc/radio0` | Modem | — |
| `/dev/emmc/sd0` | SD card | — |

### Access Control

- **Disk_Drivers group (GID 132):** grants read/write at DAC level via setgid
- **Root (uid 0):** full access, but does NOT bypass hardware write-protection
- **devuser (uid 850):** no direct access (EPERM) unless via `g_Disk_Drivers`

## 16. NVFS / vtnvfs — Token Storage

`vtnvfsd` is a FUSE filesystem that manages the `nvuser` partition containing
security tokens.

### On-Disk Format

- **Block-based** with per-file headers containing length fields
- **Hash-based file lookup** — 32-bit hash key table with collision handling
- Token files: regex `.*\.tkn$`
- Signature sidecar: `.sig.%s`

### Security Properties

- `vtnvfsd` **VERIFIES `.tkn` signatures** (ECDSA/RSA) on the OS read/write path
- `aboot` (bootloader) reads `/nvuser/hlos_unsigned.tkn` and only checks
  `state=="development"` — **NO signature check**
- An ISP write that lays the token into nvuser in RAW vtnvfs block format
  (no `.sig` sidecar) would bypass vtnvfsd's signature check entirely

---

# Part V: Security Mechanisms

## 17. Boot Chain Signing

BB10 uses a **hierarchical, sequential ECDSA P-256 signing chain**:

```
PBL (fused key, immutable root of trust)
  → verifies SBL1 signature
    → SBL1 verifies TrustZone
      → TrustZone verifies aboot
        → aboot verifies boot.img (kernel + ramdisk)
          → ramdisk contains dm-verity root-of-trust key
            → dm-verity verifies /system + /oem
```

### Key Properties

- Each stage **independently verifies the NEXT** — sequential, not simultaneous
- 4 embedded root certificates: `ABDI` (aboot), `ABBI` (boot), `APBI` (PBL),
  `ACBI` (combined)
- If ANY signature verification fails, the chain halts
- The `bbss.insecure` flag bypasses SBL1 verification only — all downstream
  stages still verify their next stage

### Signatures Found in bbss.mbn

- `"BB Attestation CA (insecure)"`
- `"BB Root CA (insecure)"`

These are the certificates used when `bbss_insecure` is set — they allow the
prototype bootloader to pass verification.

## 18. dm-verity

dm-verity provides block-level integrity verification for system partitions.

### Protected Partitions

| Mount | Device | Integrity |
|---|---|---|
| `/system` | dm-0 | dm-verity (auto-trusted by Pathtrust) |
| `/oem` | dm-1 | dm-verity (auto-trusted by Pathtrust) |
| `/data` | dm-2 | forceencrypt, **NO dm-verity** |

### Key Properties

- Root-of-trust key lives **inside** `boot.img`'s ramdisk (ECDSA-gated)
- Cannot change the verity root without a signed `boot.img`
- `/system` and `/oem` are **automatically trusted** by Pathtrust because
  they are dm-verity devices (`pathtrust_add_dev()` called at dm-verity setup)
- **No content self-healing** — device fails CLOSED everywhere
- `CONFIG_PANIC_ON_DATA_CORRUPTION=y` → tamper triggers kernel panic
- `CONFIG_MSM_FORCE_WDOG_BITE_ON_PANIC=y` + `CONFIG_PANIC_TIMEOUT=5` →
  watchdog reboot ~5 seconds after any panic

### dm-verity ↔ Pathtrust Integration

When a dm-verity target is set up, `drivers/md/dm-verity.c:979` calls
`pathtrust_add_dev(bdev->bd_dev)`, making the device automatically trusted.
This is why `/system` and `/oem` are trusted while `/data` is not.

## 19. Pathtrust — Filesystem Trust LSM

Pathtrust is the **enforcement LSM** (unlike BIDE's detection-only model).
It controls which filesystems can be used for execution, memory mapping,
module loading, and firmware loading.

### LSM Hooks (6 registered)

| Hook | Function | What It Blocks |
|---|---|---|
| `sb_mount` | `pathtrust_sb_mount` | Mount from untrusted source |
| `sb_kern_mount` | `pathtrust_sb_kern_mount` | Kern mount from untrusted |
| `bprm_set_creds` | `pathtrust_bprm_set_creds` | **Exec** from non-trusted FS |
| `mmap_file` | `pathtrust_mmap_file` | **mmap PROT_EXEC** from non-trusted |
| `kernel_fw_from_file` | `pathtrust_kernel_fw_from_file` | **Firmware load** from non-trusted |
| `kernel_module_from_file` | `pathtrust_kernel_module_from_file` | **Module load** from non-trusted |

### Enforcement

- `pathtrust_enforce = 1` (compiled in, boots enforced)
- `/sys/kernel/security/pathtrust/enforce` write path is **COMPILED OUT**
  (`CONFIG_SECURITY_PATHTRUST_DEVELOP=n`) — read-only, no runtime toggle
- **Independent of SELinux** — even after `setenforce(0)`, Pathtrust still
  enforces

### Who Is Subject to Enforcement

| Condition | Details |
|---|---|
| `is_root(cred)` | euid==0 OR egid==0 |
| `has_banned_caps()` | ANY of: CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_DAC_READ_SEARCH, CAP_FOWNER, CAP_MAC_ADMIN, CAP_MAC_OVERRIDE, CAP_MKNOD, CAP_SETGID, CAP_SETUID, CAP_SYS_ADMIN, CAP_SYS_MODULE, CAP_SYS_PTRACE, CAP_SYS_RAWIO |
| `is_forbidden_sid()` | Process SELinux sid is in Pathtrust forbidden list |

**Key implication:** An unprivileged shell (uid 2000, no banned caps, not
forbidden sid) is **NOT subject to Pathtrust enforcement**. Enforcement only
bites once root / banned caps / forbidden SELinux domain.

### Trust List

`/proc/boot/pathtrust` (root:nto, mode 750):
- `<file>` = trust filesystem
- `!<file>` = trust specific file
- `-t <file>` = query trust status
- `lockdown` = lock trust list

Trust list is re-applied every `btool` run (boot autoroot + switchzone).
Not persistent by itself.

### Non-Bypass Interfaces

- `/dev/pathtrust` ioctl `IOCTL_TRUST_FILE` = QUERY only (returns -EPERM if
  queried file is non-trusted and caller is root/banned/forbidden)
- Pathtrust netlink (`NETLINK_PATHTRUST`) = BROADCAST-ONLY, no kernel receive
  path → cannot toggle enforce from userspace
- `/dev/pathtrust` device: `crw-rw-rw-` (666, world-openable)

### Post-Root Exploit Path

Pathtrust BLOCKS:
- Exec from `/data`
- mmap PROT_EXEC from `/data`
- insmod/finit_module from `/data`
- request_firmware from `/data`

Viable post-root path: kernel write primitive → direct cred overwrite (skip
setuid) → write `hlos_unsigned.tkn` to RAW `/dev/block` nvuser (Pathtrust
does NOT hook block I/O).

## 20. BIDE — Integrity Detection

BIDE (BlackBerry Integrity Detection) is the **detection-only LSM**. It never
blocks — it only reports incidents to JBIDE userspace (DTEK).

### LSM Hooks → Sensor Mapping

| Hook | Sensor | Trigger |
|---|---|---|
| `task_create` | no-op | — |
| `task_free` | auth_remove_pid + child propagation | process exit |
| `task_fix_setuid` | SN_ESCALATED_UID/GID, SN_SYSTEM_UID | setuid/setgid syscall |
| `sb_mount` | SN_NOSUID, SN_NODEV | only if MS_NOSUID/MS_NODEV REMOVED |
| `mmap_file` | SN_LOW_MMAP_ADDR | only if mmap_min_addr < DEFAULT |
| `capset` | SN_CAPSET | only if cap not already 'allowed' |
| `bprm_set_creds` | SN_ROOT_PROCESS_DETECTOR | new root proc after snapshot |
| `file_mprotect` | SN_MPROTECT | CROSS-process only (see gap) |
| `kernel_module_init/free` | **COMPILED OUT** | `#ifdef AVEN_44469_FIXED`, never set |

### BIDE Detection Gaps (Stealth Map)

| Gap | Mechanism | Detail |
|---|---|---|
| G1 | `file_mprotect` | Returns 0 if `(vma->vm_flags & VM_SHARED)` OR `(vma->vm_mm == current->mm)`. Self-mprotect(RWX) on own memory is NEVER flagged. |
| G2 | `task_fix_setuid` | Fires on SYSCALL path. Direct kernel cred overwrite (`current->cred->uid=0`) never goes through this → never flagged. |
| G3 | `capset` | `int allowed_caps` is 32-bit but `kernel_cap_t` is 64-bit. Caps 32-63 invisible. Only flags caps NOT already allowed. |
| G4 | `sb_mount` | Only flags mounts that REMOVE nosuid/nodev. Normal bind mount WITH nosuid+nodev passes silently. |
| G5 | Snapshot gating | ALL sensors gated by `ctl_snapshot_complete()`. Before boot snapshot finishes, all return early (blind). |
| G6 | VMA scanner | `vma_scan_task()` only scans ROOT processes. Unprivileged process memory never hashed/verified. |
| G7 | Module hashing | `kernel_module_init → tz_add_section` is COMPILED OUT. BIDE does NOT hash loaded kernel modules. |

### BIDE Snapshot Mechanism

- Snapshot taken ONCE by JBIDE via `BIDE_IOCTL_TAKE_SNAPSHOT`
- If `tz_init_kernel()` fails, `taken` stays 0 FOREVER → BIDE permanently blind
- Not attacker-controllable from unprivileged

### Stealth Recipe (Avoids All BIDE Sensors)

1. Kernel write primitive → direct cred overwrite (skip setuid syscall)
2. Raw-block token write (skip file LSM / setenforce)
3. Do NOT mprotect OTHER processes
4. Do NOT mount without nosuid/nodev
5. Do NOT call setenforce(0)
6. Do NOT panic

## 21. SELinux

SELinux runs in **enforcing** mode on BB10. The shell runs as `u:r:shell:s0`.

### Policy Highlights

- Shell can binder CALL: `{ keystore, surfaceflinger }` ONLY
- Untrusted_app binder CALL: `{ keystore, dataminer }` ONLY
- fidodaemon callable by: `{ system_app, platform_app, servicemanager }` only
- Shell has NO binder rule to fidodaemon, drmserver, mediaserver, qseeproxy

### SELinux + Pathtrust Interaction

Pathtrust is INDEPENDENT of SELinux. Even after `setenforce(0)`, Pathtrust
still enforces. The `is_forbidden_sid()` check in Pathtrust uses the process
SELinux sid.

### SELinux + BIDE Interaction

BIDE detects `setenforce(0)/policy` → `SN_SELINUX_DISABLED/CHANGED` (netlink
listener). Stealth: write token to RAW nvuser block (bypasses SELinux file
check entirely; no setenforce needed).

## 22. GRSEC / PaX

BB10 kernels include **in-tree** grsecurity/PaX hardening:

| Feature | Status |
|---|---|
| `PAX_REFCOUNT` | Compiled in |
| `PAX_RANDKSTACK` | Compiled in |
| `PAX_RANDUSTACK` | Compiled in |
| `PAX_MEMORY_SANITIZE` | Compiled in |
| `PAX_MEMORY_STACKLEAK` | Compiled in |
| `PAX_MEMORY_UDEREF` | Compiled in |
| SIGKILL on violations | Compiled in |

### Impact on Exploitation

- All PaX violations result in **SIGKILL** (not SIGSEGV)
- `commit_creds` address varies per boot (no fixed gadget)
- UAF/slab exploit reliability significantly reduced
- No public BB10 kernel exploit exists

## 23. eMMC Hardware Write-Protection

The final hardware gate. Even with root, even with `/proc/as` access, the eMMC
controller enforces write-protection on boot partitions.

### How It Works

1. SBL1 reads `ext_csd[173]` (B_BOOT_WP) and sets `B_PWR_WP_EN` (bit 2)
2. The eMMC controller marks boot0/boot1 as read-only at the hardware level
3. Any write attempt returns `EROFS` (Read-only file system)
4. `ext_csd[170]` (BOOT_CONFIG_PROT) = `0x00` means the WP is temporary
   (power-on only), NOT permanent

### Why Standard CMD6 SWITCH Fails

The stock driver's `WRITE_PROTECT` devctl DOES reach `mmc_switch(0xad)`,
sending CMD6 to `ext_csd[173]`. But the **eMMC card rejects the switch** with
`SWITCH_ERROR`. Possible reasons:

1. The WP may need a vendor-specific ordering sequence (e.g., select
   `PARTITION_ACCESS` to boot0 first)
2. `B_PERM_WP_DIS` may need to be written before `B_PWR_WP_EN`
3. The eMMC may require exclusive access (filesystems unmounted)

Without `VUC_CMD` (raw MMC passthrough), the driver cannot express the
required CMD6 sequence.

---

# Part VI: Root & Unlock Methods

## 24. getroot Payload

`getroot` is the root exploit for BB10 Classic/Passport. It installs a root
payload that runs at every boot via **autoroot**.

### Components

| Component | Purpose |
|---|---|
| `btool` | Shell script — root payload orchestrator |
| `__root` | setuid-0 ELF binary — grants real uid-0 ksh |
| `ota_info_pps.sh` | Symlink — autoroot entry point |
| `g_Disk_Drivers` | setgid wrapper — grants Disk_Drivers group |

### Boot Sequence

```
Boot → autoroot triggers → ota_info_pps.sh symlink
  → btool runs AS ROOT
    → btool line 31: /proc/boot/pathtrust !/base/bin/__root
    → __root becomes "trusted" in Pathtrust
  → Later: user runs __root
    → procmgr_ability(ADN_NONROOT|MEM_PHYS) → setuid(0) → setreuid(0,0)
    → system("/bin/ksh") → real uid-0 shell
```

### Autoroot Trigger

- `btool` runs at boot (autoroot) and on switchzone
- switchzone via `__upd`: `os:true` SWITCHES the OS SLOT (drops dev-mode+SSH);
  `os:false` does NOT run btool
- Only safe `btool` trigger = boot autoroot

## 25. Group Wrappers & procmgr_ability

### Group Wrappers

~400 setgid symlink-family "group wrappers" in `/base/bin/`:
```
__USER   (setuid-user)   g_GROUP (setgid-group)   u_USER (setuid-user)
```

ALL are the same 4488-byte ELF32 ARM binary (BuildID `84c92d436dc1ffd7c62c27eccfadb2f0`). Target uid/gid is **decoded from `argv[0]`** (the filename).

### Binary RE

```
main() = getuid/getgid/getpid/geteuid/getegid
  → procmgr_ability() per ability
  → setregid(egid=target, rgid=-1)
  → setreuid
  → system("/bin/ksh")   # command is FIXED, NOT argv-injectable
```

### Usage

```bash
echo "id;groups" | /base/bin/g_Disk_Drivers
# uid=100(devuser) gid=132(Disk_Drivers) groups=132(Disk_Drivers)

echo "exec /accounts/.../python3.11 /path/py" | /base/bin/g_Disk_Drivers
# python runs with egid=Disk_Drivers
```

### Key Groups

| Group | GID | Purpose |
|---|---|---|
| `g_Disk_Drivers` | 132 | Opens `/dev/emmc/*` (block devices) |
| `g_nto` | — | QNX system |
| `g_pps` | — | Persistent Publish/Subscribe |
| `g_sys` | — | System |
| `g_rpmb` | — | RPMB access |
| `g_trustzone` | — | TrustZone bridge |
| `g_powerauth` | — | Power authentication |
| `g_filesystem` | — | Filesystem operations |

### procmgr_ability Mechanism

The `procmgr_ability()` system call grants QNX process abilities:

```c
procmgr_ability(handle,
    ADN_NONROOT | PROCMGR_AOP_ALLOW | SUBRANGE,
    PROCMGR_AID_MEM_PHYS, ...);
```

- `ADN_NONROOT` (0x20000000) — scope for non-root processes
- `ADN_ROOT` (0x10000000) — scope for root processes
- `PROCMGR_AOP_ALLOW` — allow the ability
- `SUBRANGE` — specify address range

The `__root` binary requests `MEM_PHYS` ability via `ADN_NONROOT`, but under
that scope it does NOT apply to the now-root process. This is the root cause
of the `/proc/as` ability gate regression.

## 26. pathtrust Whitelist Trick

The key to real root on BB10:

### The Trick

1. `btool` runs as root at boot (autoroot)
2. `btool` writes `!/base/bin/__root` to `/proc/boot/pathtrust`
3. `__root` becomes "trusted" in Pathtrust
4. `__root`'s setuid-0 now works (Pathtrust allows exec of trusted files)
5. Real uid-0 shell achieved

### Why This Works

Pathtrust's `bprm_set_creds` hook blocks exec from non-trusted FS when the
caller is root/banned-caps. By whitelisting `__root`, it becomes trusted,
and its setuid-0 is allowed.

### Limitations

- Trust list is re-applied every `btool` run — not persistent by itself
- `__root` can only grant abilities that are in its `procmgr_ability()` set
- The `ADN_NONROOT` scope limitation prevents `__root` from granting
  `MEMレストRICT` to itself

## 27. boot0 Modification

The theoretical unlock path — modify `boot0` to set `bbss.insecure`:

### Target

| Location | Offset | Value Needed |
|---|---|---|
| `boot0` build-info field8 | `0x35a98` | `0x00000001` (non-zero = insecure) |

### Current Blocker

`boot0` is hardware write-protected (`EROFS`). The eMMC controller rejects
all writes. The WP is temporary (`B_PWR_WP_EN`, `BOOT_CONFIG_PROT=0x00`),
but clearing it via standard CMD6 SWITCH fails (`SWITCH_ERROR`).

### Once WP Cleared

1. Write `bbss.insecure` = 1 at `boot0@0x35a98`
2. Write prototype bootloader (imggen output) to boot0
3. Reboot → SBL1 skips signature verification → prototype bootloader loads
4. Prototype bootloader enables fastboot/sideload
5. Flash LineageOS or custom OS

## 28. Prototype Bootloader Generation

`imggen` generates the prototype bootloader images that the `bbss.insecure`
flag enables.

### What imggen Produces

1. **Stage images** — stage1/2/3.mbn, bbss.mbn (compiled for target SoC)
2. **GPT templates** — secure and insecure variants
3. **HWI partition** — hardware identification text + FNV1a checksum

### passport_stage3 (MSM8974AA)

A PBL-level debug mode exploit that:

1. Runs code on the **RPM co-processor** to set magic registers
2. Forces PBL into debug mode (`BOOT_PARTITION_SELECT=0x5D1`)
3. PBL skips signature verification and loads any SBL1 from eMMC

### RPM Component

```c
GCC_WDOG_DEBUG      (0xFC401780) = 0x20000;  // disable watchdog
BOOT_PARTITION_SELECT(0xFC4BE0F0) = 0x5D1;    // PBL debug mode
apps_reset();  // reset APPS processor
```

### APPS Component

Reimplements PBL boot sequence using PBL helper functions (direct function
pointers into PBL ROM). The critical bypass:

```c
pbl_authenticate_sbl()  // STUBBED — just returns 0
                       // Completely skips signature verification
```

### Why It's Not a Software Unlock

The magic registers (`0xFC4xxxxx`) are **NOT reachable from the running OS**.
Stage3 requires the PBL to already be in download/debug mode, which is
hardware/key-gated — the same gate as EDL.

## 29. EDL / Firehose / Sahara

### EDL (Emergency Download Mode)

Qualcomm's emergency download mode for unbricking. Uses the Sahara protocol
to transfer firehose programmers.

### Status on BB10

- **No EDL/Sahara strings in SBL1** — only "factory boot mode" vs "product
  boot mode"
- **MSM8960 firehose programmer missing** — `edl loader` has Qualcomm's
  Sahara firehose loaders for MSM8974/MSM8996/MSM8998/SDM845 etc., but
  NOT for MSM8960
- **EDL is NOT a software path from the running OS** — requires PBL download
  mode entry (hardware/key-gated)

### Sahara Protocol

1. Device enters EDL mode (via PBL or hardware trigger)
2. Host connects via USB, Sahara handshake
3. Device sends `COMMAND_HELLO` with `版本=1/2`, `回环=4096`
4. Host sends `COMMAND_READ_DATA` for firehose programmer
5. Device executes firehose programmer
6. Host sends XML commands (read/write/erase)

### Passport Stage3 as EDL Alternative

Stage3 is essentially a software-triggered EDL entry for the Passport. It
uses the RPM co-processor to force PBL debug mode, achieving what EDL does
via hardware. But it requires:
1. Physical access to the device
2. The PBL to accept the debug mode trigger
3. No hardware key gate (unlike standard EDL)

---

# Part VII: Research Methodology

## 30. QNX MMC Devctl Interface

The QNX MMC devctl interface is the primary mechanism for communicating with
the eMMC driver from userspace.

### Devctl Constants

```c
#define _DCMD_CAM    0x0C
#define _SIM_MMCSD   3600
#define _SIM_SDMMC   3700

DCMD_MMCSD_GET_CID         = 0xC0101A00  // Get card ID
DCMD_MMCSD_WRITE_PROTECT   = 0xC0201A11  // Write protect control
DCMD_MMCSD_GET_CSD         = 0xC0C81A02  // Get card specific data
DCMD_MMCSD_ERASE           = 0xC0201A13  // Erase blocks
DCMD_MMCSD_CARD_REGISTER   = 0xC0181A14  // Get CARD_REGISTER
DCMD_MMCSD_GET_ECCERR_ADDR = 0xC0041A05  // Get ECC error address
DCMD_MMCSD_VUC_CMD         = 0xC0441A16  // Raw MMC command (NOT IMPLEMENTED)
```

### Encoding Formula

`(sizeof<<16)+(class<<8)+cmd+0xC0000000` with `_DCMD_CAM=0x0C`,
`_SIM_MMCSD=3600`.

### DCMD_MMCSD_WRITE_PROTECT Struct

```c
struct mmc_wp {
    uint32_t action;    // +0x00: MMCSD_WP_ACTION_CLR=0x00 / SET=0x01
    uint32_t mode;      // +0x04: MMCSD_WP_MODE_PWR_WP_EN=0x01
    uint64_t lba;       // +0x08: starting LBA
    uint64_t nlba;      // +0x10: number of LBAs
    uint64_t rsvd2;     // +0x18: reserved
};                      // total: 32 bytes
```

### Driver Dispatch Table (ARM, `0x10a0d574`)

| dcmd | Handler | Purpose |
|---|---|---|
| `0xc0181a14` | `0x10a0d492` | CARD_REGISTER |
| `0xc0201a11` | `0x10a0fcec` | WRITE_PROTECT |
| `0xc0201a13` | `0x10a0fdb4` | ERASE/group |
| `0x40011a46` | `0x10a0d620` | ext_csd byte 0xa8 (read only) |
| `0x40101a44` | `0x10a0d5f2` | CID |
| `0xc0441a16` | **ABSENT** | VUC_CMD → ENOTTY |

### WRITE_PROTECT Handler (`0x10a0fcec`)

```
Builds part entry: r6 = dev_obj + target*0x2c8 + lun*0x58 + 0x1d0
Worker at 0x10a0f48c:
  Gate: cmp.w sl,#0x1c ; bne → need sl==0x1c (28) for mmc_switch branch
  r5&7==0 → USER_WP:  mmc_switch(hba, 1, 3, 0xab, val)
  r5==2   → BOOT_WP:  mmc_switch(sb, 1, 3, 0xad, val)
mmc_switch = 0x10a076c0 → CMD6 send at 0x10a08240
```

**Critical finding:** `sl==0x1c` gate means NO action value (0-3) equals 0x1c
→ the BOOT_WP branch is **unreachable** via normal devctl encoding.

### mmc_switch Address

`mmc_switch = 0x10a076c0` (lock 0x10a053b0, CMD6-send 0x10a08240, unlock
0x10a053b0).

Needed call: `mmc_switch(hba, r1=1, r2=3, r3=0xad, value=0)`

## 31. /proc/<pid>/as Memory Patching

`/proc/<pid>/as` is the QNX process address-space file, providing read/write
access to a process's virtual memory.

### Access Requirements

- Requires `PROCMGR_AID_MEM_PHYS` ability
- Held by device managers that own hardware nodes
- Can be granted via `procmgr_ability()` (as `__root` attempts)

### Live Testing Results

| Session | State | Result |
|---|---|---|
| 7t-7u | Earlier boots | `.data`/`.bss` WRITABLE, `.text` READ-ONLY |
| 7r | sdmmc driver | `deadbeef` written to `.data@0x10fe9630`, read back OK |
| 11c-11d | Current boot | **EPERM** for ALL contexts (root, python, etc.) |

### Regression

Earlier sessions had `/proc/as` R/W; current boot does not grant the ability.
Root cause: `__root`'s `procmgr_ability()` requests `MEM_PHYS` via
`ADN_NONROOT`, but under that scope it does NOT apply to the now-root process.

### Implications for Driver Patching

Without `/proc/as` write access, the in-driver patching approach is blocked:

1. Cannot read sdmmc driver's `.text` at runtime
2. Cannot write a Thumb thunk to redirect WP dispatch
3. Cannot test `.text` writability (which was confirmed READ-ONLY in earlier sessions)

## 32. Reverse Engineering

### Tools Used

| Tool | Purpose |
|---|---|
| Ghidra | Binary RE, decompilation, control flow analysis |
| radare2 (r2) | Disassembly, string analysis, cross-references |
| capstone | Instruction decoding (Thumb-2) |
| strings / hexdump | Quick reconnaissance |

### Key Binaries RE'd

| Binary | Size | Key Findings |
|---|---|---|
| `devb-sdmmc-rim-msmsdcc` | — | MMC driver dispatch table, WRITE_PROTECT handler, mmc_switch address |
| `__root` | 4,488 B | procmgr_ability → setuid → ksh; ADN_NONROOT scope at offsets 0x860, 0x884 |
| `g_Disk_Drivers` | 4,488 B | setgid wrapper, decodes target from argv[0] |
| `mmcsdpub` | 23,600 B | MMCSD publisher, reads DEVINFO, publishes PPS fields |
| `bbss.mbn` | — | bbss_insecure flag semantics, boot WP type |
| `passport_stage3` | — | RPM→PBL debug mode exploit, PBL function table |

### RE Methodology

1. **String extraction** — identify function names, error messages, debug strings
2. **Dispatch table mapping** — trace devctl handlers through compare-and-branch chains
3. **Cross-reference analysis** — find all callers of key functions (mmc_switch, procmgr_ability)
4. **Live verification** — confirm RE findings against running device (slog2, devctl calls)

## 33. Live Debugging

### Connection Setup

Every session requires fresh SSH connection:

```bash
# 1. Verify link
ping -c1 -W2 169.254.0.1

# 2. Verify SSH listener
echo > /dev/tcp/169.254.0.1/22

# 3. Connect with key
python3 connect_now.py
```

### Required Patches

QNX sshd only accepts RSA-SHA1 signatures:
- `server_sig_algs=False` (monkeypatch of `Transport.__init__`)
- `disabled_algorithms={'pubkeys':['rsa-sha2-512','rsa-sha2-256']}`

### blackberry-connect

Must stay running — pushes `authorized_keys` and establishes tunnel:
```bash
nohup "$BC" 169.254.0.1 -password <DEV_PW> \
  -sshPublicKey id_rsa.pub > /tmp/opencode/bb_connect.log 2>&1 &
```

### Key Debugging Commands

```bash
# Read eMMC registers via devctl
echo "dcmd ..." | /base/bin/g_Disk_Drivers

# Check partition status
cat /pps/qnx/disk/<dev>/status

# Read ext_csd via CARD_REGISTER
cat /proc/<pid>/as  # (if ability granted)

# Check slog2 for driver messages
slog2info | grep sdmmc
```

---

# Part VIII: Status & Open Questions

## 34. Current State

### Classic (MSM8960)

| Capability | Status |
|---|---|
| Root (uid 0) | **ACHIEVED** — via getroot + pathtrust whitelist trick |
| eMMC read | **ACHIEVED** — via g_Disk_Drivers setgid wrapper |
| boot0 dump | **ACHIEVED** — 4 MB recovered to dumps/ |
| boot0 write | **BLOCKED** — hardware write-protect (EROFS) |
| Bootloader unlock | **BLOCKED** — single byte at boot0@0x35a98 |
| /proc/as access | **BLOCKED** — ability-gated, regression on current boot |

### Passport (MSM8974AA)

| Capability | Status |
|---|---|
| Root (uid 0) | **ACHIEVED** — same getroot method |
| eMMC read | **ACHIEVED** — same group wrapper |
| boot0 write | **BLOCKED** — same hardware WP |
| Stage3 exploit | **MAPPED** — RPM→PBL debug mode, but not software-reachable |

## 35. B_PWR_WP_EN Clearing

The eMMC card rejects the standard CMD6 SWITCH to clear `ext_csd[173]`. The
driver reaches `mmc_switch(0xad)` but gets `SWITCH_ERROR`.

### Possible Solutions

1. **Vendor-specific CMD6 sequence** — select `PARTITION_ACCESS` (ext_csd[179])
   to boot0 first, then write B_PWR_WP_EN
2. **B_PERM_WP_DIS ordering** — write permanent-WP-disable before power-on-WP
3. **Exclusive access** — unmount all filesystems, ensure no concurrent access
4. **Raw CMD6 passthrough** — `VUC_CMD` (not implemented in stock driver)

### Status

Route A (standard WRITE_PROTECT) is **confirmed dead end**. The 8d-vs-8e
contradiction is resolved in favor of 8e — the card genuinely rejects the switch,
not an encoding issue.

## 36. /proc/as Ability Gate

`/proc/<pid>/as` requires `PROCMGR_AID_MEM_PHYS` ability, which is not granted
to root processes on the current boot.

### Root Cause

`__root`'s `procmgr_ability()` requests `MEM_PHYS` via `ADN_NONROOT` scope.
Under `ADN_NONROOT`, the ability does NOT apply to the now-root process. The
ability grant is session/boot-dependent.

### The Wall

- Every process (including pid 1) lacks `MEM_PHYS` on current boot
- `procmgr_ability(ADN_ROOT)` from root may not work (root may lack authority
  to self-grant an ability not in its set)
- SSH-as-root userauth hangs server-side (sshd bug in this QNX build)

## 37. Future Work

### Software Paths

1. **Raw CMD6 passthrough** — patch `VUC_CMD` into driver dispatch table
   (requires `/proc/as` write or driver binary modification)
2. **Driver thread hijack** — via `/proc/<pid>/ctl` + debug API
   (`DCMD_PROC_STOP` / `SETGREG`)
3. **Native ARM probe** — build with QNX cross-compiler, test ADN_ROOT
   self-grant from root context

### Hardware Paths

4. **ISP (no-desolder)** — test point access to eMMC, bypass OS entirely
5. **Desolder eMMC** — direct chip-out and rework

### Priv (Android)

6. **Kernel LPE** — grsecurity/PaX hardened, no public exploit
7. **nvuser token write** — not HW write-protected; needs raw block access
8. **vtnvfsd bypass** — aboot doesn't verify token signature

---

# Appendices

See the companion files in `docs/structure/`:

- [Appendix A: Device Specifications](docs/structure/appendix-a-device-specs.md)
- [Appendix B: Partition Layouts](docs/structure/appendix-b-partition-layouts.md)
- [Appendix C: Filesystem Mounts](docs/structure/appendix-c-filesystem-mounts.md)
- [Appendix D: Devctl Constants](docs/structure/appendix-d-devctl-constants.md)
- [Appendix E: Security Policy](docs/structure/appendix-e-security-policy.md)
- [Appendix F: Session Index](docs/structure/appendix-f-session-index.md)
- [Appendix G: Glossary](docs/structure/appendix-g-glossary.md)

---

> **Document version:** September 2026
>
> Built from research sessions 7b through 11d (March–September 2026).
> Cross-referenced with GPL sources (`imggen`, `passport_stage3`,
> `asroot_main.c`) and live device testing on Classic (MSM8960) and
> Passport (MSM8974AA).
